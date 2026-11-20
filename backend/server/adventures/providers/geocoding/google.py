from typing import Dict, List

import requests

from core.results import ProviderResult

# Google's Maps Platform terms allow caching only place IDs and coordinates, so Google
# results are never cached here. See documentation/docs/configuration/caching.md.

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"


def reverse_geocode(lat: float, lon: float, api_key: str) -> ProviderResult[Dict]:
    if not api_key:
        return ProviderResult(error="Google Maps API key not configured")

    params = {"latlng": f"{lat},{lon}", "key": api_key}

    try:
        response = requests.get(GEOCODE_URL, params=params, timeout=(2, 5))
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return ProviderResult(error="Request timed out while contacting Google Maps")
    except requests.exceptions.RequestException:
        return ProviderResult(error="Google Maps service error")

    data = response.json() or {}
    status = data.get("status")
    if status and status != "OK":
        return ProviderResult(error=f"Google Maps geocoding error: {status}")

    return ProviderResult(data=data)


def search_nearby_place_names(lat: float, lon: float, api_key: str) -> ProviderResult[List[str]]:
    """Display names of the places within a few metres of a point, nearest first."""
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
        response = requests.post(NEARBY_URL, headers=headers, json=payload, timeout=(2, 5))
        response.raise_for_status()
        places = (response.json() or {}).get("places", [])
    except requests.exceptions.RequestException:
        return ProviderResult(error="Google Maps nearby search error")

    return ProviderResult(data=[((place.get("displayName") or {}).get("text")) for place in places])
