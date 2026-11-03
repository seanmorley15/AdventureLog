from typing import Dict, List

import requests

from core.results import ProviderResult
from django.conf import settings
from core.cache import cached_provider, coordinate_key

GOOGLE_CACHE_TIMEOUT = getattr(settings, 'GOOGLE_API_CACHE_TIMEOUT', 60 * 60 * 24)

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"
NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"

SEARCH_FIELD_MASK = (
    "places.id,places.displayName.text,places.formattedAddress,places.location,"
    "places.types,places.rating,places.userRatingCount,places.websiteUri,"
    "places.nationalPhoneNumber,places.internationalPhoneNumber,"
    "places.editorialSummary.text,places.googleMapsUri,places.photos.name"
)

DETAILS_FIELD_MASK = (
    "id,displayName.text,formattedAddress,editorialSummary.text,types,"
    "rating,userRatingCount,websiteUri,nationalPhoneNumber,"
    "internationalPhoneNumber,googleMapsUri,reviews.text.text"
)

NEARBY_FIELD_MASK = "places.displayName.text,places.formattedAddress,places.types"


@cached_provider(
    'google_places_search',
    lambda query, api_key=None, max_results=20, *a, **k: (query, max_results),
    GOOGLE_CACHE_TIMEOUT,
)
def search_places(query: str, api_key: str, max_results: int = 20) -> ProviderResult[List[Dict]]:
    if not api_key:
        return ProviderResult(error="Google Maps API key not configured")

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": SEARCH_FIELD_MASK,
    }
    payload = {
        "textQuery": query,
        "maxResultCount": max_results,
    }

    try:
        response = requests.post(SEARCH_URL, json=payload, headers=headers, timeout=(2, 5))
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return ProviderResult(error="Request timed out while contacting Google Maps")
    except requests.exceptions.RequestException:
        return ProviderResult(error="Google Maps service error")

    data = response.json() or {}
    return ProviderResult(data=data.get("places", []))


@cached_provider('google_place_details', lambda place_id, *a, **k: (place_id,), GOOGLE_CACHE_TIMEOUT)
def fetch_place_details(place_id: str, api_key: str) -> ProviderResult[Dict]:
    if not api_key:
        return ProviderResult(error="Google Maps API key not configured")

    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": DETAILS_FIELD_MASK,
    }

    try:
        response = requests.get(
            DETAILS_URL.format(place_id=place_id),
            headers=headers,
            timeout=(2, 6),
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return ProviderResult(error="Request timed out while contacting Google Maps")
    except requests.exceptions.RequestException:
        return ProviderResult(error="Google Maps service error")

    return ProviderResult(data=response.json() or {})


@cached_provider(
    'google_places_nearby',
    lambda lat, lon, api_key=None, radius=45.0, *a, **k: (
        coordinate_key(lat, 4),
        coordinate_key(lon, 4),
        radius,
    ),
    GOOGLE_CACHE_TIMEOUT,
)
def search_nearby(lat: float, lon: float, api_key: str, radius: float = 45.0) -> ProviderResult[List[Dict]]:
    if not api_key:
        return ProviderResult(error="Google Maps API key not configured")

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": NEARBY_FIELD_MASK,
    }
    payload = {
        "maxResultCount": 6,
        "rankPreference": "DISTANCE",
        "locationRestriction": {
            "circle": {
                "center": {"latitude": float(lat), "longitude": float(lon)},
                "radius": float(radius),
            }
        },
    }

    try:
        response = requests.post(NEARBY_URL, headers=headers, json=payload, timeout=(2, 5))
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return ProviderResult(error="Google Maps service error")

    data = response.json() or {}
    return ProviderResult(data=data.get("places", []))
