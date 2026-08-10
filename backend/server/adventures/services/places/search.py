import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from django.conf import settings

from adventures.providers.places.google import search_places as google_search
from adventures.providers.places.osm import search_places as osm_search


@dataclass
class PlaceSearchResult:
    lat: Optional[float]
    lon: Optional[float]
    name: Optional[str]
    display_name: Optional[str]
    place_id: Optional[str]
    type: Optional[str]
    types: List[str]
    category: Optional[str]
    description: Optional[str]
    website: Optional[str]
    phone_number: Optional[str]
    google_maps_url: Optional[str]
    importance: Optional[float]
    rating: Optional[float]
    review_count: Optional[int]
    photos: List[str]
    addresstype: Optional[str]
    provider: Optional[str]
    powered_by: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lat": self.lat,
            "lon": self.lon,
            "name": self.name,
            "display_name": self.display_name,
            "place_id": self.place_id,
            "type": self.type,
            "types": self.types,
            "category": self.category,
            "description": self.description,
            "website": self.website,
            "phone_number": self.phone_number,
            "google_maps_url": self.google_maps_url,
            "importance": self.importance,
            "rating": self.rating,
            "review_count": self.review_count,
            "photos": self.photos,
            "addresstype": self.addresstype,
            "provider": self.provider,
            "powered_by": self.powered_by,
        }


@dataclass
class ProviderSearchResult:
    provider_used: Optional[str]
    providers_attempted: List[str] = field(default_factory=list)
    results: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None


def _safe_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _extract_google_category(types: List[str]) -> Optional[str]:
    if not types:
        return None
    if "restaurant" in types:
        return "food"
    if "lodging" in types:
        return "accommodation"
    if "park" in types or "natural_feature" in types:
        return "nature"
    if "museum" in types or "tourist_attraction" in types:
        return "attraction"
    if "locality" in types or "administrative_area_level_1" in types:
        return "region"
    return types[0]


def _infer_addresstype(type_name: Optional[str]) -> Optional[str]:
    mapping = {
        "locality": "city",
        "sublocality": "neighborhood",
        "administrative_area_level_1": "region",
        "administrative_area_level_2": "county",
        "country": "country",
        "premise": "building",
        "point_of_interest": "poi",
        "route": "road",
        "street_address": "address",
    }
    return mapping.get(type_name, None)


def _normalize_google_search_results(places: List[Dict[str, Any]], api_key: str) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []

    for place in places or []:
        location = place.get("location", {}) or {}
        types = place.get("types", []) or []
        primary_type = types[0] if types else None
        category = _extract_google_category(types)
        addresstype = _infer_addresstype(primary_type)

        rating = _safe_float(place.get("rating"))
        review_count = _safe_int(place.get("userRatingCount"))
        importance = None
        if rating is not None and review_count:
            importance = round(float(rating) * float(review_count) / 100, 2)

        photos = []
        for photo in place.get("photos", [])[:5]:
            photo_name = photo.get("name")
            if photo_name:
                photos.append(
                    f"https://places.googleapis.com/v1/{photo_name}/media?key={api_key}&maxHeightPx=800&maxWidthPx=800"
                )

        display_name_obj = place.get("displayName", {}) or {}
        name = display_name_obj.get("text") if isinstance(display_name_obj, dict) else display_name_obj

        normalized.append(
            PlaceSearchResult(
                lat=_safe_float(location.get("latitude")),
                lon=_safe_float(location.get("longitude")),
                name=name,
                display_name=place.get("formattedAddress"),
                place_id=place.get("id"),
                type=primary_type,
                types=types,
                category=category,
                description=(place.get("editorialSummary") or {}).get("text"),
                website=place.get("websiteUri"),
                phone_number=place.get("internationalPhoneNumber")
                or place.get("nationalPhoneNumber"),
                google_maps_url=place.get("googleMapsUri"),
                importance=importance,
                rating=rating,
                review_count=review_count,
                photos=photos,
                addresstype=addresstype,
                provider="google",
                powered_by="google",
            ).to_dict()
        )

    if normalized:
        normalized.sort(
            key=lambda r: r.get("importance") if r.get("importance") is not None else 0,
            reverse=True,
        )

    return normalized


def _normalize_osm_search_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []

    for item in results or []:
        normalized.append(
            PlaceSearchResult(
                lat=_safe_float(item.get("lat")),
                lon=_safe_float(item.get("lon")),
                name=item.get("name"),
                display_name=item.get("display_name"),
                place_id=None,
                type=item.get("type"),
                types=[],
                category=item.get("category"),
                description=None,
                website=None,
                phone_number=None,
                google_maps_url=None,
                importance=_safe_float(item.get("importance")),
                rating=None,
                review_count=None,
                photos=[],
                addresstype=item.get("addresstype"),
                provider="osm",
                powered_by="nominatim",
            ).to_dict()
        )

    return normalized


def _query_looks_like_coordinates(query: str) -> bool:
    if not query:
        return False
    return bool(re.match(r"^\s*-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?\s*$", query))


def _score_search_result(result: Dict[str, Any], query: str) -> float:
    score = 0.0
    importance = result.get("importance")
    if importance is not None:
        try:
            score += math.log1p(abs(float(importance)))
        except (TypeError, ValueError):
            pass

    rating = result.get("rating")
    if rating is not None:
        try:
            score += float(rating) / 5.0
        except (TypeError, ValueError):
            pass

    review_count = result.get("review_count")
    if review_count is not None:
        try:
            score += math.log1p(float(review_count)) / 3.0
        except (TypeError, ValueError):
            pass

    if result.get("place_id"):
        score += 0.5

    query_normalized = (query or "").strip().lower()
    if query_normalized:
        haystack = f"{result.get('name', '')} {result.get('display_name', '')}".lower()
        if query_normalized in haystack:
            score += 1.5

    return score


def _score_search_results(results: List[Dict[str, Any]], query: str) -> float:
    if not results:
        return 0.0
    scores = sorted((_score_search_result(item, query) for item in results), reverse=True)
    top_scores = scores[:5]
    if not top_scores:
        return 0.0
    return sum(top_scores) / len(top_scores)


def _search_result_key(result: Dict[str, Any]) -> str:
    name = (result.get("name") or result.get("display_name") or "").strip().lower()
    lat = result.get("lat")
    lon = result.get("lon")
    lat_value = round(float(lat), 5) if lat is not None else ""
    lon_value = round(float(lon), 5) if lon is not None else ""
    return f"{name}:{lat_value}:{lon_value}"


def _merge_search_results(
    primary: List[Dict[str, Any]],
    secondary: List[Dict[str, Any]],
    limit: int = 20,
) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen = set()
    for item in (primary or []) + (secondary or []):
        key = _search_result_key(item)
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
        if len(merged) >= limit:
            break
    return merged


def _should_compare_osm(query: str, google_results: List[Dict[str, Any]]) -> bool:
    if _query_looks_like_coordinates(query):
        return True
    if not google_results:
        return True
    if len(google_results) < 3:
        return True
    return _score_search_results(google_results, query) < 1.5


def search_places(query: str, max_results: int = 20) -> ProviderSearchResult:
    normalized_query = str(query or "").strip()
    if not normalized_query:
        return ProviderSearchResult(
            provider_used=None,
            results=[],
            error="Query parameter is required",
        )

    providers_attempted: List[str] = []
    google_results: Optional[List[Dict[str, Any]]] = None
    osm_results: Optional[List[Dict[str, Any]]] = None
    google_error: Optional[str] = None
    osm_error: Optional[str] = None

    api_key = getattr(settings, "GOOGLE_MAPS_API_KEY", None)
    if api_key:
        providers_attempted.append("google")
        google_payload = google_search(normalized_query, api_key=api_key, max_results=max_results)
        if google_payload.error:
            google_error = google_payload.error
        else:
            google_results = _normalize_google_search_results(google_payload.data, api_key)

    if google_results is None or _should_compare_osm(normalized_query, google_results):
        providers_attempted.append("osm")
        osm_payload = osm_search(normalized_query, limit=max_results)
        if osm_payload.error:
            osm_error = osm_payload.error
        else:
            osm_results = _normalize_osm_search_results(osm_payload.data)

    provider_used: Optional[str] = None
    results: List[Dict[str, Any]] = []

    if google_results and osm_results:
        google_score = _score_search_results(google_results, normalized_query)
        osm_score = _score_search_results(osm_results, normalized_query)
        score_gap = abs(google_score - osm_score)
        score_floor = max(google_score, osm_score, 0.1)

        if score_gap / score_floor <= 0.15:
            provider_used = "mixed"
            results = _merge_search_results(google_results, osm_results, limit=max_results)
        elif google_score >= osm_score:
            provider_used = "google"
            results = google_results
        else:
            provider_used = "osm"
            results = osm_results
    elif google_results:
        provider_used = "google"
        results = google_results
    elif osm_results:
        provider_used = "osm"
        results = osm_results
    else:
        error_message = google_error or osm_error or "No locations found for the given query."
        return ProviderSearchResult(
            provider_used=None,
            providers_attempted=providers_attempted,
            results=[],
            error=error_message,
        )

    return ProviderSearchResult(
        provider_used=provider_used,
        providers_attempted=providers_attempted,
        results=results,
    )
