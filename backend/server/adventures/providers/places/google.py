from typing import Dict, List

import requests

from adventures.providers.base import ProviderResult

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
