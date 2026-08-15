from typing import Any, Dict, List, Optional
import logging
from geopy.distance import geodesic
from django.conf import settings

from adventures.providers.recommendations import google as google_reco_provider
from adventures.providers.recommendations import osm as osm_reco_provider

logger = logging.getLogger(__name__)


def calculate_quality_score(place_data: Dict[str, Any]) -> float:
    import math

    score = 0.0
    rating = place_data.get("rating")
    if rating is not None and rating > 0:
        score += (rating / 5.0) * 50

    review_count = place_data.get("review_count")
    if review_count is not None and review_count > 0:
        score += min(30, math.log10(review_count) * 10)

    distance_km = place_data.get("distance_km")
    if distance_km is not None:
        if distance_km < 1:
            score += 20
        elif distance_km < 5:
            score += 15
        elif distance_km < 10:
            score += 10
        elif distance_km < 20:
            score += 5

    if place_data.get("is_verified") or place_data.get("business_status") == "OPERATIONAL":
        score += 10

    photos = place_data.get("photos")
    if photos and len(photos) > 0:
        score += 5

    opening_hours = place_data.get("opening_hours")
    if opening_hours and len(opening_hours) > 0:
        score += 5

    return round(score, 2)


def _parse_google_places(places: List[Dict[str, Any]], origin: Optional[tuple]) -> List[Dict[str, Any]]:
    locations: List[Dict[str, Any]] = []
    api_key = getattr(settings, "GOOGLE_MAPS_API_KEY", None)

    for place in places or []:
        location = place.get("location", {}) or {}
        types = place.get("types", []) or []

        display_name = place.get("displayName") or place.get("display_name")
        name = display_name.get("text") if isinstance(display_name, dict) else display_name

        lat = location.get("latitude")
        lon = location.get("longitude")
        if lat is None or lon is None or not name:
            continue

        rating = place.get("rating")
        review_count = place.get("userRatingCount") or 0

        # Filtering thresholds
        if rating and rating < 3.0:
            continue
        if review_count and review_count < 5:
            continue

        distance_km = None
        if origin:
            try:
                distance_km = round(geodesic(origin, (float(lat), float(lon))).km, 2)
            except Exception:
                distance_km = None

        formatted_address = place.get("formattedAddress") or place.get("shortFormattedAddress")
        business_status = place.get("businessStatus")
        opening_hours = place.get("regularOpeningHours")
        current_opening = place.get("currentOpeningHours") or {}
        is_open_now = current_opening.get("openNow")

        photos = place.get("photos", []) or []
        photo_urls = []
        if photos and api_key:
            for photo in photos[:5]:
                # v1 API returns photo entries with a 'name' attribute. Legacy API returns 'photo_reference'.
                photo_name = photo.get("name")
                if photo_name:
                    photo_urls.append(f"https://places.googleapis.com/v1/{photo_name}/media?key={api_key}&maxHeightPx=800&maxWidthPx=800")
                    continue
                photo_ref = photo.get('photo_reference')
                if photo_ref:
                    # Fallback to legacy photo endpoint
                    photo_urls.append(f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_ref}&key={api_key}")

        place_data = {
            "id": f"google:{place.get('id')}",
            "external_id": place.get("id"),
            "source": "google",
            "name": name,
            "description": (place.get("editorialSummary") or {}).get("text") if isinstance(place.get("editorialSummary"), dict) else None,
            "latitude": lat,
            "longitude": lon,
            "address": formatted_address,
            "distance_km": distance_km,
            "rating": rating,
            "review_count": review_count,
            "price_level": place.get("priceLevel"),
            "types": types,
            "primary_type": types[0] if types else None,
            "business_status": business_status,
            "is_open_now": is_open_now,
            "opening_hours": opening_hours.get("weekdayDescriptions") if opening_hours else None,
            "phone_number": place.get("nationalPhoneNumber") or place.get("internationalPhoneNumber"),
            "website": place.get("websiteUri"),
            "google_maps_url": place.get("googleMapsUri"),
            "photos": photo_urls,
            "is_verified": business_status == "OPERATIONAL",
        }

        place_data["quality_score"] = calculate_quality_score(place_data)
        locations.append(place_data)

    return locations


def _parse_overpass(data: Dict[str, Any], origin: Optional[tuple]) -> List[Dict[str, Any]]:
    nodes = data.get("elements", []) or []
    locations: List[Dict[str, Any]] = []

    for node in nodes:
        if node.get("type") not in ["node", "way", "relation"]:
            continue

        tags = node.get("tags", {}) or {}
        lat = node.get("lat") or node.get("center", {}).get("lat")
        lon = node.get("lon") or node.get("center", {}).get("lon")
        name = tags.get("name") or tags.get("official_name") or tags.get("alt_name")
        if not name or lat is None or lon is None:
            continue

        distance_km = None
        if origin:
            try:
                distance_km = round(geodesic(origin, (float(lat), float(lon))).km, 2)
            except Exception:
                distance_km = None

        address_parts = [
            tags.get('addr:housenumber'),
            tags.get('addr:street'),
            tags.get('addr:suburb') or tags.get('addr:neighbourhood'),
            tags.get('addr:city'),
            tags.get('addr:state'),
            tags.get('addr:postcode'),
            tags.get('addr:country')
        ]
        formatted_address = ", ".join([p for p in address_parts if p]) or None

        types = [tags.get(k) for k in ['tourism', 'leisure', 'amenity', 'natural', 'historic', 'attraction', 'shop', 'sport'] if tags.get(k)]
        primary_type = types[0] if types else None

        if not primary_type:
            continue
        if tags.get('disused') or tags.get('construction'):
            continue

        place_data = {
            "id": f"osm:{node.get('type')}:{node.get('id')}",
            "external_id": str(node.get('id')),
            "source": "osm",
            "name": name,
            "description": tags.get('description') or tags.get('note'),
            "latitude": lat,
            "longitude": lon,
            "address": formatted_address,
            "distance_km": distance_km,
            "rating": None,
            "review_count": None,
            "price_level": None,
            "types": types,
            "primary_type": primary_type,
            "business_status": None,
            "is_open_now": None,
            "opening_hours": [tags.get('opening_hours')] if tags.get('opening_hours') else None,
            "phone_number": tags.get('phone') or tags.get('contact:phone'),
            "website": tags.get('website') or tags.get('contact:website') or tags.get('url'),
            "google_maps_url": None,
            "photos": [tags.get('image')] if tags.get('image') else [],
            "is_verified": bool(tags.get('wikipedia') or tags.get('wikidata')),
            "osm_type": node.get('type'),
            "wikipedia": tags.get('wikipedia'),
        }

        place_data['quality_score'] = calculate_quality_score(place_data)
        locations.append(place_data)

    return locations


def _deduplicate_results(google_results: List[Dict[str, Any]], osm_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from difflib import SequenceMatcher

    def is_similar(name1: str, name2: str, threshold: float = 0.85) -> bool:
        return SequenceMatcher(None, (name1 or "").lower(), (name2 or "").lower()).ratio() > threshold

    def is_nearby(loc1: Dict[str, Any], loc2: Dict[str, Any], max_distance_m: int = 50) -> bool:
        try:
            dist = geodesic((loc1['latitude'], loc1['longitude']), (loc2['latitude'], loc2['longitude'])).meters
            return dist < max_distance_m
        except Exception:
            return False

    dedup = list(google_results or [])
    for osm_loc in osm_results or []:
        duplicate = False
        for google_loc in google_results or []:
            if is_similar(osm_loc.get('name', ''), google_loc.get('name', '')) and is_nearby(osm_loc, google_loc):
                duplicate = True
                break
        if not duplicate:
            dedup.append(osm_loc)
    return dedup


def get_recommendations(lat: float, lon: float, radius: float, category: str, sources: str = 'both') -> Dict[str, Any]:
    api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
    origin = (float(lat), float(lon))

    google_results: List[Dict[str, Any]] = []
    osm_results: List[Dict[str, Any]] = []
    osm_error = None

    included_types_map = {
        'lodging': ['lodging', 'hotel', 'hostel', 'resort_hotel', 'extended_stay_hotel'],
        'food': ['restaurant', 'cafe', 'bar', 'bakery', 'meal_takeaway', 'meal_delivery'],
        # Remove types unsupported by Google Places v1 (e.g. 'natural_feature')
        'tourism': ['tourist_attraction', 'museum', 'art_gallery', 'aquarium', 'zoo', 'amusement_park', 'park'],
    }

    included_types = included_types_map.get(category, ['tourist_attraction'])

    if api_key and sources in ['google', 'both']:
        # Google Places v1 enforces maxResultCount between 1 and 20
        provider_payload = google_reco_provider.search_nearby(lat, lon, radius, api_key, included_types, max_results=20)
        if provider_payload.error:
            logger.warning(f"Google recommendations provider error: {provider_payload.error}")
        else:
            google_results = _parse_google_places(provider_payload.data or [], origin)

    if sources in ['osm', 'both'] or (sources == 'google' and not google_results):
        if category == 'tourism':
            query = f"""
                [out:json][timeout:25];
                (
                  nwr["tourism"~"attraction|viewpoint|museum|gallery|zoo|aquarium"](around:{min(radius,5000)},{lat},{lon});
                  nwr["leisure"~"park|garden|nature_reserve"](around:{min(radius,5000)},{lat},{lon});
                );
                out center tags 50;
                """
        elif category == 'lodging':
            query = f"""
                [out:json][timeout:25];
                nwr["tourism"~"hotel|motel|guest_house|hostel"](around:{min(radius,5000)},{lat},{lon});
                out center tags 50;
                """
        else:
            query = f"""
                [out:json][timeout:25];
                nwr["amenity"~"restaurant|cafe|bar|pub|fast_food|bakery"](around:{min(radius,5000)},{lat},{lon});
                out center tags 50;
                """

        osm_payload = osm_reco_provider.execute_overpass_query(query)
        if osm_payload.error:
            osm_error = osm_payload.error
            logger.warning(f"OSM recommendations provider error: {osm_error}")
        else:
            osm_results = _parse_overpass(osm_payload.data or {}, origin)

    if sources == 'both' and google_results and osm_results:
        all_results = _deduplicate_results(google_results, osm_results)
    else:
        all_results = (google_results or []) + (osm_results or [])

    all_results.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
    limited = all_results[:50]

    response = {
        'count': len(limited),
        'results': limited,
        'sources_used': {
            'google': len(google_results),
            'osm': len(osm_results),
            'total_before_dedup': len(google_results) + len(osm_results)
        }
    }

    if osm_error and len(osm_results) == 0:
        response['warnings'] = [osm_error]

    return response
