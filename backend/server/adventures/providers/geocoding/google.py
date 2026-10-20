from typing import Dict, List

import requests

from core.results import ProviderResult
from django.conf import settings
from core.cache import cached_provider, coordinate_key

GOOGLE_CACHE_TIMEOUT = getattr(settings, 'GOOGLE_API_CACHE_TIMEOUT', 60 * 60 * 24)

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"


# The key is left out of the cache key, so the cached result is shared.
@cached_provider(
    'google_reverse',
    lambda lat, lon, *a, **k: (coordinate_key(lat, 5), coordinate_key(lon, 5)),
    GOOGLE_CACHE_TIMEOUT,
)
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
