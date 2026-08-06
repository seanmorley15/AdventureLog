from dataclasses import dataclass
from typing import Any, Dict, Optional

from django.conf import settings

from adventures.providers.geocoding.google import reverse_geocode as google_reverse
from adventures.providers.geocoding.osm import reverse_geocode as osm_reverse
from adventures.utils.geocoding_utils import (
    _extract_google_location_name,
    _extract_osm_location_name,
    _fetch_google_nearby_place_name,
    _parse_google_address_components,
    extractIsoCode,
)


@dataclass
class ReverseGeocodeResult:
    data: Dict[str, Any]
    provider_used: Optional[str]


def _normalize_google_geocode_payload(payload: Dict[str, Any], lat: float, lon: float, api_key: str) -> Dict[str, Any]:
    results = (payload or {}).get("results", []) or []
    if not results:
        return {"error": "No location found for the given coordinates."}

    nearby_place_name = _fetch_google_nearby_place_name(lat, lon, api_key)
    location_name = _extract_google_location_name(results, nearby_place_name=nearby_place_name)

    first_result = results[0]
    address_result = next(
        (result for result in results if "plus_code" not in result.get("types", [])),
        first_result,
    )

    return {
        "name": first_result.get("formatted_address"),
        "location_name": location_name,
        "address": _parse_google_address_components(address_result.get("address_components", [])),
    }


def _reverse_geocode_quality(result: Dict[str, Any]) -> int:
    if not result or result.get("error"):
        return 0

    score = 0
    if result.get("region_id"):
        score += 3
    if result.get("city_id"):
        score += 2
    if result.get("country_id"):
        score += 1
    if result.get("location_name"):
        score += 1
    if result.get("display_name"):
        score += 1
    return score


def reverse_geocode(lat: float, lon: float, user) -> ReverseGeocodeResult:
    google_result = None

    api_key = getattr(settings, "GOOGLE_MAPS_API_KEY", None)
    if api_key:
        google_payload = google_reverse(lat, lon, api_key)
        if not google_payload.error:
            normalized_google = _normalize_google_geocode_payload(
                google_payload.data, lat=lat, lon=lon, api_key=api_key
            )
            if normalized_google.get("error"):
                google_result = normalized_google
            else:
                google_result = extractIsoCode(user, normalized_google)
                if isinstance(google_result, dict) and "error" not in google_result:
                    google_result["provider_used"] = "google"
                    google_result["provider"] = "google"

    if google_result and not google_result.get("error"):
        if _reverse_geocode_quality(google_result) >= 5:
            return ReverseGeocodeResult(data=google_result, provider_used="google")

    osm_payload = osm_reverse(lat, lon)
    osm_result = None
    if not osm_payload.error:
        osm_data = osm_payload.data
        osm_data["location_name"] = _extract_osm_location_name(osm_data)
        osm_result = extractIsoCode(user, osm_data)
        if isinstance(osm_result, dict) and "error" not in osm_result:
            osm_result["provider_used"] = "osm"
            osm_result["provider"] = "osm"

    if osm_result and not osm_result.get("error"):
        if google_result and not google_result.get("error"):
            google_score = _reverse_geocode_quality(google_result)
            osm_score = _reverse_geocode_quality(osm_result)
            best = google_result if google_score >= osm_score else osm_result
            used = "google" if best is google_result else "osm"
            return ReverseGeocodeResult(data=best, provider_used=used)

        return ReverseGeocodeResult(data=osm_result, provider_used="osm")

    if google_result:
        return ReverseGeocodeResult(data=google_result, provider_used="google")

    return ReverseGeocodeResult(data=osm_result or {"error": "Unable to reverse geocode location."}, provider_used=None)
