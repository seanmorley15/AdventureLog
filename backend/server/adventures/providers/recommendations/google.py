from typing import Dict, List

import requests

from core.results import ProviderResult

# Google's Maps Platform terms allow caching only place IDs and coordinates, so Google
# results are never cached here. See documentation/docs/configuration/caching.md.

NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"

# Only the fields the results use, as Google's policy asks (and cheaper).
FIELD_MASK = (
    "places.id,"
    "places.displayName.text,"
    "places.formattedAddress,"
    "places.location,"
    "places.types,"
    "places.rating,"
    "places.userRatingCount,"
    "places.businessStatus,"
    "places.priceLevel,"
    "places.websiteUri,"
    "places.googleMapsUri,"
    "places.nationalPhoneNumber,"
    "places.editorialSummary.text,"
    "places.photos.name,"
    "places.currentOpeningHours.openNow,"
    "places.regularOpeningHours.weekdayDescriptions"
)


def search_nearby(
    lat: float,
    lon: float,
    radius: float,
    api_key: str,
    included_types: List[str],
    max_results: int = 20,
    language_code: str = '',
) -> ProviderResult[List[Dict]]:
    if not api_key:
        return ProviderResult(error="Google Maps API key not configured")

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    payload = {
        "includedTypes": included_types,
        "maxResultCount": max_results,
        "rankPreference": "POPULARITY",
        **({"languageCode": language_code} if language_code else {}),
        "locationRestriction": {
            "circle": {
                "center": {"latitude": float(lat), "longitude": float(lon)},
                "radius": float(radius),
            }
        },
    }

    try:
        response = requests.post(NEARBY_URL, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return ProviderResult(error="Google Places API timeout")
    except requests.exceptions.RequestException as e:
        # If v1 API returns 400 Bad Request, attempt legacy Places NearbySearch as a fallback
        try:
            status = getattr(e.response, 'status_code', None)
        except Exception:
            status = None

        if status == 400:
            # Legacy NearbySearch
            try:
                legacy_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
                params = {
                    'key': api_key,
                    'location': f"{lat},{lon}",
                    'radius': int(min(radius, 50000)),
                    # Use the first included type as the 'type' or use keyword
                }
                if included_types:
                    params['type'] = included_types[0]
                if language_code:
                    params['language'] = language_code

                legacy_resp = requests.get(legacy_url, params=params, timeout=10)
                legacy_resp.raise_for_status()
                legacy_data = legacy_resp.json() or {}
                places = []
                for item in legacy_data.get('results', [])[:max_results]:
                    loc = item.get('geometry', {}).get('location', {})
                    photos = item.get('photos') or []
                    places.append({
                        'id': item.get('place_id'),
                        'displayName': item.get('name'),
                        'formattedAddress': item.get('vicinity') or item.get('formatted_address'),
                        'location': {'latitude': loc.get('lat'), 'longitude': loc.get('lng')},
                        'types': item.get('types'),
                        'rating': item.get('rating'),
                        'userRatingCount': item.get('user_ratings_total') or item.get('userRatingCount'),
                        'businessStatus': None,
                        'priceLevel': item.get('price_level'),
                        'websiteUri': None,
                        'googleMapsUri': None,
                        'nationalPhoneNumber': None,
                        'internationalPhoneNumber': None,
                        'editorialSummary': None,
                        'photos': [{'photo_reference': p.get('photo_reference')} for p in photos],
                        'currentOpeningHours': {'openNow': item.get('opening_hours', {}).get('open_now')} if item.get('opening_hours') else None,
                        'regularOpeningHours': None,
                    })

                return ProviderResult(data=places)
            except requests.exceptions.RequestException:
                return ProviderResult(error="Google Places API error")

        return ProviderResult(error="Google Places API error")

    data = response.json() or {}
    return ProviderResult(data=data.get("places", []))
