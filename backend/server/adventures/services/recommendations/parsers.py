"""Turn Google Places and Overpass payloads into one result shape."""

from typing import Any, Dict, List, Optional

from adventures.services.places.photos import proxy_photo_url

from .merge import haversine_m

PRICE_LEVELS = {
    'PRICE_LEVEL_FREE': 0,
    'PRICE_LEVEL_INEXPENSIVE': 1,
    'PRICE_LEVEL_MODERATE': 2,
    'PRICE_LEVEL_EXPENSIVE': 3,
    'PRICE_LEVEL_VERY_EXPENSIVE': 4,
}
OSM_TYPE_TAGS = ('tourism', 'leisure', 'amenity', 'natural', 'historic', 'attraction', 'shop', 'sport')
MIN_RATING = 3.0
MIN_REVIEWS_FOR_RATING_FILTER = 10


def normalize_price_level(value: Any) -> Optional[int]:
    """Google v1 sends enum names, the legacy API sends 0-4."""
    if isinstance(value, int) and 0 <= value <= 4:
        return value
    return PRICE_LEVELS.get(value)


def _distance_km(origin: Optional[tuple], lat: float, lon: float) -> Optional[float]:
    if not origin:
        return None
    try:
        return round(haversine_m(origin[0], origin[1], float(lat), float(lon)) / 1000.0, 2)
    except (TypeError, ValueError):
        return None


def _google_photo_urls(photos: List[Dict[str, Any]]) -> List[str]:
    """App addresses for a place's photos; the Google key stays on the server."""
    urls: List[str] = []
    for photo in photos[:5]:
        if photo.get('name'):
            urls.append(proxy_photo_url(name=photo['name']))
        elif photo.get('photo_reference'):
            urls.append(proxy_photo_url(reference=photo['photo_reference']))
    return urls


def parse_google_places(places: List[Dict[str, Any]], origin: Optional[tuple], category: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for place in places or []:
        location = place.get('location') or {}
        lat, lon = location.get('latitude'), location.get('longitude')
        display_name = place.get('displayName')
        name = display_name.get('text') if isinstance(display_name, dict) else display_name
        place_id = place.get('id')
        if lat is None or lon is None or not name or not place_id:
            continue
        if place.get('businessStatus') in ('CLOSED_PERMANENTLY', 'CLOSED_TEMPORARILY'):
            continue

        rating = place.get('rating')
        review_count = place.get('userRatingCount') or 0
        if rating and rating < MIN_RATING and review_count >= MIN_REVIEWS_FOR_RATING_FILTER:
            continue

        types = place.get('types') or []
        regular_hours = place.get('regularOpeningHours') or {}
        summary = place.get('editorialSummary')
        business_status = place.get('businessStatus')
        results.append(
            {
                'id': f'google:{place_id}',
                'external_id': place_id,
                'place_id': place_id,
                'source': 'google',
                'category': category,
                'name': name,
                'description': summary.get('text') if isinstance(summary, dict) else None,
                'latitude': lat,
                'longitude': lon,
                'address': place.get('formattedAddress') or place.get('shortFormattedAddress'),
                'distance_km': _distance_km(origin, lat, lon),
                'rating': rating,
                'review_count': review_count,
                'price_level': normalize_price_level(place.get('priceLevel')),
                'types': types,
                'primary_type': types[0] if types else None,
                'business_status': business_status,
                'is_open_now': (place.get('currentOpeningHours') or {}).get('openNow'),
                'opening_hours': regular_hours.get('weekdayDescriptions') or None,
                'phone_number': place.get('nationalPhoneNumber') or place.get('internationalPhoneNumber'),
                'website': place.get('websiteUri'),
                'google_maps_url': place.get('googleMapsUri'),
                'photos': _google_photo_urls(place.get('photos') or []),
                'is_verified': business_status == 'OPERATIONAL',
            }
        )
    return results


def parse_overpass(data: Dict[str, Any], origin: Optional[tuple], category: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for element in (data or {}).get('elements', []) or []:
        if element.get('type') not in ('node', 'way', 'relation'):
            continue
        tags = element.get('tags') or {}
        center = element.get('center') or {}
        lat = element['lat'] if element.get('lat') is not None else center.get('lat')
        lon = element['lon'] if element.get('lon') is not None else center.get('lon')
        name = tags.get('name') or tags.get('official_name') or tags.get('alt_name')
        if not name or lat is None or lon is None:
            continue
        if tags.get('disused') or tags.get('construction') or tags.get('abandoned'):
            continue
        types = [tags[k] for k in OSM_TYPE_TAGS if tags.get(k)]
        if not types:
            continue

        street = ' '.join(p for p in (tags.get('addr:street'), tags.get('addr:housenumber')) if p)
        address = ', '.join(
            p
            for p in (street, tags.get('addr:suburb') or tags.get('addr:neighbourhood'), tags.get('addr:city'),
                      tags.get('addr:state'), tags.get('addr:postcode'), tags.get('addr:country'))
            if p
        ) or None
        hours = tags.get('opening_hours')
        results.append(
            {
                'id': f"osm:{element['type']}:{element.get('id')}",
                'external_id': str(element.get('id')),
                'place_id': None,
                'source': 'osm',
                'category': category,
                'name': name,
                'description': tags.get('description') or tags.get('note'),
                'latitude': lat,
                'longitude': lon,
                'address': address,
                'distance_km': _distance_km(origin, lat, lon),
                'rating': None,
                'review_count': None,
                'price_level': None,
                'types': types,
                'primary_type': types[0],
                'business_status': None,
                'is_open_now': None,
                'opening_hours': [hours] if hours else None,
                'phone_number': tags.get('phone') or tags.get('contact:phone'),
                'website': tags.get('website') or tags.get('contact:website') or tags.get('url'),
                'google_maps_url': None,
                'photos': [tags['image']] if str(tags.get('image', '')).startswith('http') else [],
                'is_verified': bool(tags.get('wikipedia') or tags.get('wikidata')),
                'osm_type': element['type'],
                'wikipedia': tags.get('wikipedia'),
                'wikidata': tags.get('wikidata'),
                'stars': tags.get('stars'),
                'cuisine': tags.get('cuisine'),
            }
        )
    return results
