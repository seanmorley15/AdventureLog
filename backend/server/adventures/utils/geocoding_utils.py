import re
import socket
import unicodedata
from typing import Any, Dict, Optional

import requests
from django.conf import settings
from worldtravel.models import City, Region, VisitedCity, VisitedRegion


def _clean_location_candidate(value):
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _looks_like_street_address(value):
    candidate = _clean_location_candidate(value)
    if not candidate:
        return False

    lowered = candidate.lower()
    if not re.search(r"\d", lowered):
        return False

    if lowered.count(",") >= 2:
        return True

    if not re.match(r"^\d{1,6}\s+\S+", lowered):
        return False

    street_tokens = (
        "st",
        "street",
        "rd",
        "road",
        "ave",
        "avenue",
        "blvd",
        "boulevard",
        "dr",
        "drive",
        "ln",
        "lane",
        "ct",
        "court",
        "pl",
        "place",
        "pkwy",
        "parkway",
        "hwy",
        "highway",
        "trl",
        "trail",
    )
    return any(re.search(rf"\b{token}\b", lowered) for token in street_tokens)


def _first_preferred_location_name(candidates, allow_address_fallback=False):
    address_fallback = None
    for candidate in candidates:
        cleaned = _clean_location_candidate(candidate)
        if not cleaned:
            continue
        if not _looks_like_street_address(cleaned):
            return cleaned
        if address_fallback is None:
            address_fallback = cleaned
    return address_fallback if allow_address_fallback else None


def _extract_google_component_name(address_components):
    preferred_types = (
        "premise",
        "point_of_interest",
        "establishment",
        "subpremise",
        "natural_feature",
        "airport",
        "park",
        "tourist_attraction",
        "shopping_mall",
        "university",
        "school",
        "hospital",
    )

    for preferred_type in preferred_types:
        for component in address_components or []:
            types = component.get("types", [])
            if preferred_type in types:
                return component.get("long_name") or component.get("short_name")
    return None


def _score_google_result_types(types):
    priority = (
        "point_of_interest",
        "establishment",
        "premise",
        "subpremise",
        "tourist_attraction",
        "park",
        "airport",
        "shopping_mall",
        "university",
        "school",
        "hospital",
        "street_address",
        "route",
    )
    for idx, type_name in enumerate(priority):
        if type_name in types:
            return len(priority) - idx
    return 0


def _extract_osm_location_name(data):
    address = data.get("address", {}) or {}
    namedetails = data.get("namedetails", {}) or {}
    extratags = data.get("extratags", {}) or {}

    candidates = [
        data.get("name"),
        namedetails.get("name"),
        namedetails.get("official_name"),
        namedetails.get("short_name"),
        namedetails.get("brand"),
        namedetails.get("loc_name"),
        address.get("amenity"),
        address.get("tourism"),
        address.get("attraction"),
        address.get("building"),
        address.get("shop"),
        address.get("leisure"),
        address.get("historic"),
        address.get("man_made"),
        address.get("office"),
        address.get("aeroway"),
        address.get("railway"),
        address.get("public_transport"),
        address.get("craft"),
        address.get("house_name"),
        extratags.get("name"),
        extratags.get("official_name"),
        extratags.get("brand"),
        extratags.get("operator"),
    ]

    preferred = _first_preferred_location_name(candidates, allow_address_fallback=False)
    if preferred:
        return preferred

    return _first_preferred_location_name(
        [data.get("name"), data.get("display_name")],
        allow_address_fallback=True,
    )


def _parse_google_address_components(components):
    parsed = {}
    country_code = None
    state_code = None

    for comp in components:
        types = comp.get("types", [])
        long_name = comp.get("long_name")
        short_name = comp.get("short_name")

        if "country" in types:
            parsed["country"] = long_name
            country_code = short_name
            parsed["ISO3166-1"] = short_name
        if "administrative_area_level_1" in types:
            parsed["state"] = long_name
            state_code = short_name
        if "administrative_area_level_2" in types:
            parsed["county"] = long_name
        if "administrative_area_level_3" in types:
            parsed["municipality"] = long_name
        if "locality" in types:
            parsed["city"] = long_name
        if "postal_town" in types:
            parsed.setdefault("city", long_name)
        if "sublocality" in types or any(t.startswith("sublocality_level_") for t in types):
            parsed["suburb"] = long_name
        if "neighborhood" in types:
            parsed["neighbourhood"] = long_name
        if "route" in types:
            parsed["road"] = long_name
        if "street_address" in types:
            parsed["address"] = long_name

    if country_code and state_code:
        parsed["ISO3166-2-lvl1"] = f"{country_code}-{state_code}"

    return parsed


def _fetch_google_nearby_place_name(lat, lon, api_key):
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName.text,places.formattedAddress,places.types",
    }
    payload = {
        "maxResultCount": 6,
        "rankPreference": "DISTANCE",
        "locationRestriction": {
            "circle": {
                "center": {"latitude": float(lat), "longitude": float(lon)},
                "radius": 45.0,
            }
        },
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=(2, 5))
        response.raise_for_status()
        places = (response.json() or {}).get("places", [])
    except requests.exceptions.RequestException:
        return None

    candidates = [((place.get("displayName") or {}).get("text")) for place in places]
    return _first_preferred_location_name(candidates, allow_address_fallback=False)


def _extract_google_location_name(results, nearby_place_name=None):
    preferred_nearby = _first_preferred_location_name([nearby_place_name], allow_address_fallback=False)
    if preferred_nearby:
        return preferred_nearby

    scored_candidates = []
    for result in results or []:
        score = _score_google_result_types(result.get("types", []))
        if score <= 0:
            continue
        component_name = _extract_google_component_name(result.get("address_components", []))
        name_candidate = _first_preferred_location_name([component_name], allow_address_fallback=False)
        if name_candidate:
            scored_candidates.append((score, name_candidate))

    if scored_candidates:
        scored_candidates.sort(key=lambda item: item[0], reverse=True)
        return scored_candidates[0][1]

    component_candidates = [
        _extract_google_component_name(result.get("address_components", []))
        for result in (results or [])
    ]
    component_pick = _first_preferred_location_name(component_candidates, allow_address_fallback=False)
    if component_pick:
        return component_pick

    formatted_candidates = [result.get("formatted_address") for result in (results or [])]
    return _first_preferred_location_name(formatted_candidates, allow_address_fallback=True)


def is_host_resolvable(hostname: str) -> bool:
    try:
        socket.gethostbyname(hostname)
        return True
    except socket.error:
        return False


def extractIsoCode(user, data):
    iso_code = None
    display_name = None
    country_code = None
    city = None
    visited_city = None
    location_name = _clean_location_candidate(data.get("location_name") or data.get("name"))

    address = data.get("address", {}) or {}
    country_code = address.get("ISO3166-1")
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

    def _normalize_name(value):
        normalized = unicodedata.normalize("NFKD", value)
        ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
        return re.sub(r"[^a-z0-9]", "", ascii_only.lower())

    def match_locality(key_name, target_region):
        value = address.get(key_name)
        if not value:
            return None
        qs = City.objects.filter(region=target_region)

        exact_match = qs.filter(name__iexact=value).first()
        if exact_match:
            return exact_match

        normalized_value = _normalize_name(value)
        for candidate in qs.values_list("id", "name"):
            candidate_id, candidate_name = candidate
            if _normalize_name(candidate_name) == normalized_value:
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
