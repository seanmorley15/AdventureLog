"""Matching a provider's address to the Country, Region and City rows AdventureLog knows.

Nothing here names a place. A provider's address is tied to the world dataset through the
dataset's own fields: region ids, names in both languages, the regions that are also countries
(``Region.territory``) and coordinates. See ``worldtravel.territories`` for how those links are
worked out.
"""

import math
import re

from django.contrib.gis.db.models.functions import Distance

from adventures.services.geocoding.naming import clean_location_candidate
from core.geo import distance_km, make_point
from worldtravel.models import City, Country, Region, VisitedCity
from worldtravel.naming import name_keys, normalize_name
from worldtravel.visited import is_region_visited

# How far a point can be from a city or region centre and still be taken to be in it.
COORDINATE_MATCH_KM = 30

# Address fields that name a division, then one that names a populated place, most specific first.
REGION_NAME_FIELDS = (
    "state", "province", "region", "state_district", "county", "district", "territory",
    "municipality", "island", "archipelago",
)
LOCALITY_NAME_FIELDS = (
    "hamlet", "quarter", "neighbourhood", "neighborhood", "locality", "suburb", "borough",
    "city_district", "village", "town", "city",
)
# Address fields that can name a country other than the one the provider reports.
COUNTRY_NAME_FIELDS = ("country", "territory", "state", "region", "county", "municipality")


def _nearest(queryset, lat, lon, max_km):
    """The row of ``queryset`` closest to a point, if it is within ``max_km``."""
    point = make_point(lon, lat)
    if point is None:
        return None
    # A degree of longitude is shorter away from the equator, so the box is widened to cover it.
    degrees = max_km / (111.0 * max(math.cos(math.radians(lat)), 0.1))
    row = (
        queryset.filter(coordinates__dwithin=(point, degrees))
        .annotate(distance=Distance("coordinates", point))
        .order_by("distance")
        .first()
    )
    if row is not None and row.distance.km <= max_km:
        return row
    return None


def _linked_territory(address, iso_candidates, reported_code):
    """The code of the country that the dataset says this place really is, or None."""
    subdivision_ids = [c for c in iso_candidates if len(str(c)) > 2]
    if subdivision_ids:
        linked = (
            Region.objects.filter(id__in=subdivision_ids, territory__isnull=False)
            .select_related("territory")
            .first()
        )
        if linked:
            return linked.territory.country_code

    if reported_code:
        # Google names the parent's subdivision ("Guadeloupe" under France) rather than a code.
        wanted = set()
        for field in ("state", "territory", "region", "county"):
            wanted |= name_keys(address.get(field), alternatives=False)
        if wanted:
            for region in Region.objects.filter(
                country__country_code=reported_code, territory__isnull=False
            ).select_related("territory"):
                known = name_keys(region.name, alternatives=False) | name_keys(region.native_name, alternatives=False)
                if wanted & known:
                    return region.territory.country_code
    return None


def _country_named_in_address(address, reported_code, lat, lon):
    """
    The code of a country other than the reported one that the address names, or None.

    A provider can report a territory under its parent and still name the territory itself
    ("Aruba" under the Netherlands, "Åland" under Finland). A name that is one of the reported
    country's own regions is not counted, and when the coordinates are known the place has to
    be nearer the named country than the reported one.
    """
    index = {}
    centres = {}
    for code, name, native, coordinates in Country.objects.values_list(
        "country_code", "name", "native_name", "coordinates"
    ):
        centres[code] = coordinates
        for key in name_keys(name) | name_keys(native):
            index.setdefault(key, set()).add(code)

    own_region_keys = None
    for field in COUNTRY_NAME_FIELDS:
        keys = name_keys(address.get(field))
        if not keys:
            continue
        if field != "country":
            if own_region_keys is None:
                own_region_keys = set()
                if reported_code:
                    for name, native in Region.objects.filter(country__country_code=reported_code).values_list(
                        "name", "native_name"
                    ):
                        own_region_keys |= name_keys(name) | name_keys(native)
            if keys & own_region_keys:
                continue

        codes = set()
        for key in keys:
            codes |= index.get(key, set())
        codes.discard(reported_code)
        if lat is not None and lon is not None and reported_code in centres:
            own = centres[reported_code]
            codes = {
                code for code in codes
                if centres[code] is None or own is None
                or distance_km(lat, lon, centres[code].y, centres[code].x) < distance_km(lat, lon, own.y, own.x)
            }
        if len(codes) == 1:
            return codes.pop()
    return None


def _iso_without_leading_zeros(value):
    match = re.match(r"^([A-Za-z]{2})-0*(\d+)$", str(value))
    return f"{match.group(1).upper()}-{match.group(2)}" if match else None


def _unique_region_by_name(regions, address, fields):
    """The one region whose name is the value of an address field, trying the fields in order."""
    index = {}
    for region_id, name, native in regions:
        for key in name_keys(name) | name_keys(native):
            index.setdefault(key, set()).add(region_id)
    for field in fields:
        hits = set()
        for key in name_keys(address.get(field)):
            hits |= index.get(key, set())
        if len(hits) == 1:
            return hits.pop()
    return None


def _unique_region_by_city_name(country_code, address):
    """The one region holding a city named like an address field, trying the fields in order."""
    fields = [f for f in (*LOCALITY_NAME_FIELDS, "municipality", "county") if address.get(f)]
    wanted = {f: name_keys(address.get(f)) for f in fields}
    if not any(wanted.values()):
        return None
    every_key = set().union(*wanted.values())
    regions_by_key = {}
    for name, region_id in City.objects.filter(region__country__country_code=country_code).values_list(
        "name", "region_id"
    ).iterator():
        key = normalize_name(name)
        if key in every_key:
            regions_by_key.setdefault(key, set()).add(region_id)
    for field in fields:
        hits = set()
        for key in wanted[field]:
            hits |= regions_by_key.get(key, set())
        if len(hits) == 1:
            return hits.pop()
    return None


def _find_region_in_country(country_code, address, iso_candidates, lat, lon):
    """
    A region of a country for an address that the region ids and the state name did not settle.

    Tried in order: the country's only region, an id that differs only in leading zeros, a region
    named by the address, a city named by the address, and the nearest city or region.
    """
    regions = list(Region.objects.filter(country__country_code=country_code).select_related("country"))
    if not regions:
        return None
    if len(regions) == 1:
        return regions[0]
    by_id = {region.id: region for region in regions}

    plain_ids = {}
    for region in regions:
        key = _iso_without_leading_zeros(region.id)
        if key:
            plain_ids[key] = region
    for candidate in iso_candidates:
        key = _iso_without_leading_zeros(candidate)
        if key in plain_ids:
            return plain_ids[key]

    named = [(region.id, region.name, region.native_name) for region in regions]
    region_id = (
        _unique_region_by_name(named, address, REGION_NAME_FIELDS)
        or _unique_region_by_name(named, address, LOCALITY_NAME_FIELDS)
        or _unique_region_by_city_name(country_code, address)
    )
    if region_id:
        return by_id[region_id]

    if lat is not None and lon is not None:
        city = _nearest(
            City.objects.filter(region__country__country_code=country_code).select_related("region__country"),
            lat, lon, COORDINATE_MATCH_KM,
        )
        if city:
            return city.region
        return _nearest(
            Region.objects.filter(country__country_code=country_code).select_related("country"),
            lat, lon, COORDINATE_MATCH_KM,
        )
    return None


def find_region_for_point(country_code, lat, lon):
    """The region of a country that a point falls in, from the dataset alone. Makes no provider call."""
    return _find_region_in_country(country_code, {}, [], lat, lon)


def _region_of_another_country(address, iso_candidates, reported_code, lat, lon):
    """
    A region of a different country right at the point, for an address whose own country had none.

    Only when the provider gave a subdivision code the dataset does not know, or no division or
    place at all: either means the provider's country is not the whole story. Otherwise a point
    near a border would be handed to the neighbour.
    """
    if lat is None or lon is None:
        return None
    if not Country.objects.filter(country_code=reported_code).exists():
        # A country the dataset does not know cannot be second-guessed from a position.
        return None
    unknown_subdivision = any(len(str(c)) > 2 for c in iso_candidates)
    names_a_place = any(address.get(f) for f in (*REGION_NAME_FIELDS, *LOCALITY_NAME_FIELDS))
    if not unknown_subdivision and names_a_place:
        return None

    candidates = []
    city = _nearest(
        City.objects.exclude(region__country__country_code=reported_code).select_related("region__country"),
        lat, lon, COORDINATE_MATCH_KM,
    )
    if city:
        candidates.append((city.distance.km, city.region))
    region = _nearest(
        Region.objects.exclude(country__country_code=reported_code).select_related("country"),
        lat, lon, COORDINATE_MATCH_KM,
    )
    if region:
        candidates.append((region.distance.km, region))
    return min(candidates, key=lambda item: item[0])[1] if candidates else None


def extract_iso_code(user, data, lat=None, lon=None):
    iso_code = None
    display_name = None
    country_code = None
    city = None
    location_name = clean_location_candidate(data.get("location_name") or data.get("name"))

    address = data.get("address", {}) or {}
    # Nominatim leaves out the ISO3166 keys for some places (e.g. Gibraltar)
    country_code = address.get("ISO3166-1") or (address.get("country_code") or "").upper() or None
    state_name = address.get("state")

    preferred_iso_keys = (
        [
            "ISO3166-2-lvl10",
            "ISO3166-2-lvl9",
            "ISO3166-2-lvl8",
            "ISO3166-2-lvl4",
            "ISO3166-2-lvl6",
            "ISO3166-2-lvl7",
            "ISO3166-2-lvl5",
            "ISO3166-2-lvl3",
            "ISO3166-2-lvl2",
            "ISO3166-2-lvl1",
            "ISO3166-2",
        ]
        if country_code == "FR"
        else [
            "ISO3166-2-lvl10",
            "ISO3166-2-lvl9",
            "ISO3166-2-lvl8",
            "ISO3166-2-lvl4",
            "ISO3166-2-lvl7",
            "ISO3166-2-lvl6",
            "ISO3166-2-lvl5",
            "ISO3166-2-lvl3",
            "ISO3166-2-lvl2",
            "ISO3166-2-lvl1",
            "ISO3166-2",
        ]
    )

    iso_candidates = []
    for key in preferred_iso_keys:
        value = address.get(key)
        if value and value not in iso_candidates:
            iso_candidates.append(value)

    if not iso_candidates and "ISO3166-1" in address:
        iso_candidates.append(address.get("ISO3166-1"))

    iso_code = iso_candidates[0] if iso_candidates else None

    # Some places are a country of their own in the dataset but are reported under their parent
    # (Guadeloupe as a region of France). Once the country is settled, only that country's
    # regions can be the answer.
    territory_code = _linked_territory(address, iso_candidates, country_code)
    if territory_code:
        country_code = territory_code

    region_candidates = []
    for candidate in iso_candidates:
        if len(str(candidate)) <= 2:
            continue
        match = Region.objects.select_related("country").filter(id=candidate).first()
        if match and territory_code and match.country.country_code != territory_code:
            continue
        if match and match not in region_candidates:
            region_candidates.append(match)

    region = region_candidates[0] if region_candidates else None

    if not region and state_name:
        region_queryset = Region.objects.filter(name__iexact=state_name)
        if country_code:
            region_queryset = region_queryset.filter(country__country_code=country_code)
        region = region_queryset.first()
        if region:
            iso_code = region.id
            if not country_code:
                country_code = region.country.country_code
            if region not in region_candidates:
                region_candidates.insert(0, region)

    if not region and not territory_code:
        named_country = _country_named_in_address(address, country_code, lat, lon)
        if named_country:
            country_code = named_country

    if not region and country_code:
        region = _find_region_in_country(country_code, address, iso_candidates, lat, lon)
        if not region:
            region = _region_of_another_country(address, iso_candidates, country_code, lat, lon)
            if region:
                country_code = region.country.country_code
        if region:
            iso_code = region.id
            region_candidates = [region]

    if region and region.territory:
        # A region the dataset also lists as a country (found by name or by position): the
        # answer is that country's own region.
        country_code = region.territory.country_code
        region = _find_region_in_country(country_code, address, iso_candidates, lat, lon)
        region_candidates = [region] if region else []
        iso_code = region.id if region else None

    country_only = None
    if not region:
        # The country is known but nothing finer could be settled, which is still worth keeping.
        country_only = Country.objects.filter(country_code=country_code).first() if country_code else None
        if not country_only:
            return {"error": "No region found"}

    if country_only:
        return {
            "region_id": None,
            "region": None,
            "country": country_only.name,
            "country_id": country_only.country_code,
            "region_visited": False,
            "display_name": f"{country_only.name}, {country_only.country_code}",
            "city": None,
            "city_id": None,
            "city_visited": False,
            "location_name": location_name,
        }

    if not country_code:
        country_code = region.country.country_code

    region_visited = False
    city_visited = False

    locality_keys = [
        "suburb",
        "neighbourhood",
        "neighborhood",
        "city",
        "city_district",
        "town",
        "village",
        "hamlet",
        "locality",
        "municipality",
        "county",
    ]

    normalized_names_by_region = {}

    def normalized_city_names(target_region):
        # Read and normalize a region's cities once, however many address keys are tried.
        if target_region.pk not in normalized_names_by_region:
            normalized_names_by_region[target_region.pk] = [
                (city_id, normalize_name(city_name))
                for city_id, city_name in City.objects.filter(region=target_region).values_list("id", "name")
            ]
        return normalized_names_by_region[target_region.pk]

    def match_locality(key_name, target_region):
        value = address.get(key_name)
        if not value:
            return None
        qs = City.objects.filter(region=target_region)

        exact_match = qs.filter(name__iexact=value).first()
        if exact_match:
            return exact_match

        normalized_value = normalize_name(value)
        if normalized_value:
            for candidate_id, candidate_name in normalized_city_names(target_region):
                if candidate_name == normalized_value:
                    return qs.filter(id=candidate_id).first()

        if key_name == "county":
            return None

        return qs.filter(name__icontains=value).first()

    chosen_region = region
    for candidate_region in region_candidates or [region]:
        for key_name in locality_keys:
            city = match_locality(key_name, candidate_region)
            if city:
                chosen_region = candidate_region
                iso_code = chosen_region.id
                break
        if city:
            break

    region = chosen_region
    iso_code = region.id
    region_visited = is_region_visited(user.id, region)

    if city:
        display_name = f"{city.name}, {region.name}, {country_code or region.country.country_code}"
        city_visited = VisitedCity.objects.filter(city=city, user=user).exists()
    else:
        display_name = f"{region.name}, {country_code or region.country.country_code}"

    return {
        "region_id": iso_code,
        "region": region.name,
        "country": region.country.name,
        "country_id": region.country.country_code,
        "region_visited": region_visited,
        "display_name": display_name,
        "city": city.name if city else None,
        "city_id": city.id if city else None,
        "city_visited": city_visited,
        "location_name": location_name,
    }
