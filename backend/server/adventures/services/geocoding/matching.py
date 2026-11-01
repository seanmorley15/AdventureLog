"""Matching a provider's address to the Region and City rows AdventureLog knows."""

import re
import unicodedata

from adventures.services.geocoding.naming import clean_location_candidate
from worldtravel.models import City, Region, VisitedCity, VisitedRegion

# ISO 3166-2 subdivisions that the travel database stores as their own country.
# Geocoders may report the subdivision (e.g. Åland as FI-01) instead of the country (AX).
SUBDIVISION_COUNTRY_CODES = {
    "FI-01": "AX",
    "NL-CW": "CW",
    "NL-SX": "SX",
}

# Nominatim localizes Åland. The dataset stores the Swedish municipality name, and
# Mariehamn is the one whose Finnish name differs. The municipality field is often
# the sub-region ("Mariehamn sub-region", "Mariehamns stad", "Maarianhaminan kaupunki")
# rather than the municipality itself.
ALAND_LOCALIZED_NAMES = {
    "maarianhamina": "mariehamn",
    "maarianhaminankaupunki": "mariehamn",
    "mariehamnsstad": "mariehamn",
    "mariehamnsubregion": "mariehamn",
}


def _normalize_name(value):
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", ascii_only.lower())


def _aland_name_keys(value):
    """Normalized form, plus the Swedish municipality name when Nominatim localized it."""
    key = _normalize_name(value)
    alias = ALAND_LOCALIZED_NAMES.get(key)
    if alias and alias != key:
        return (key, alias)
    return (key,)


def _match_named_region(regions, value):
    cleaned = clean_location_candidate(value)
    if not cleaned:
        return None
    wanted = set(_aland_name_keys(cleaned))
    for region in regions:
        if _normalize_name(region.name) in wanted:
            return region
    return None


def extract_iso_code(user, data):
    iso_code = None
    display_name = None
    country_code = None
    city = None
    visited_city = None
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

    region_candidates = []
    for candidate in iso_candidates:
        if len(str(candidate)) <= 2:
            continue
        match = Region.objects.filter(id=candidate).first()
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

    if not region and country_code:
        # Countries without subdivisions are imported as a single "<CC>-00" region
        region = Region.objects.filter(id=f"{country_code}-00").first()
        if region:
            iso_code = region.id
            region_candidates.append(region)

    if not region:
        alias_country = next(
            (SUBDIVISION_COUNTRY_CODES[c] for c in iso_candidates if c in SUBDIVISION_COUNTRY_CODES),
            None,
        )
        if alias_country:
            alias_regions = list(Region.objects.filter(country__country_code=alias_country))
            if len(alias_regions) == 1:
                # Curaçao and Sint Maarten import as one "<CC>-00" region.
                region = alias_regions[0]
            else:
                # Åland imports as 16 municipalities. Nominatim puts the municipality
                # in "municipality" or, when that field is the wider sub-region, in "town".
                for field in ("municipality", "town"):
                    region = _match_named_region(alias_regions, address.get(field))
                    if region:
                        break
            if region:
                iso_code = region.id
                region_candidates = [region]
                country_code = alias_country

    if not region:
        return {"error": "No region found"}

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
                (city_id, _normalize_name(city_name))
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

        normalized_value = _normalize_name(value)
        if target_region.country.country_code == "AX":
            acceptable = set(_aland_name_keys(value))
        else:
            acceptable = {normalized_value}
        for candidate_id, candidate_name in normalized_city_names(target_region):
            if candidate_name in acceptable:
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
    visited_region = VisitedRegion.objects.filter(region=region, user=user).first()
    region_visited = bool(visited_region)

    if city:
        display_name = f"{city.name}, {region.name}, {country_code or region.country.country_code}"
        visited_city = VisitedCity.objects.filter(city=city, user=user).first()
        city_visited = bool(visited_city)
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
