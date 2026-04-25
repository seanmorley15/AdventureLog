from urllib.parse import urlparse

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from rest_framework import status
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
from rest_framework.response import Response

from adventures.geocoding import get_place_details
from adventures.models import Collection


def coerce_coordinate(value, min_value, max_value):
    try:
        number = round(float(value), 6)
    except (TypeError, ValueError):
        return None

    if number < min_value or number > max_value:
        return None

    return number


def coerce_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def coerce_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def coerce_bool(value, default=False):
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False

    return default


def clean_url(value):
    if not isinstance(value, str):
        return None

    normalized = value.strip()
    if not normalized:
        return None

    parsed = urlparse(normalized)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return normalized

    return None


def sanitize_tags(raw_tags, max_tags=8):
    if not isinstance(raw_tags, list):
        return []

    tags = []
    for item in raw_tags:
        if not isinstance(item, str):
            continue

        value = item.strip()
        if not value or value in tags:
            continue

        tags.append(value)
        if len(tags) >= max_tags:
            break

    return tags


def sanitize_photo_urls(raw_urls, max_urls=5):
    if not isinstance(raw_urls, list):
        return []

    cleaned = []
    for value in raw_urls:
        url = clean_url(value)
        if not url or url in cleaned:
            continue

        cleaned.append(url)
        if len(cleaned) >= max_urls:
            break

    return cleaned


def build_quick_add_description(base_description, detailed_description):
    description = str(detailed_description or "").strip() or str(base_description or "").strip()
    return description or None


def resolve_quick_add_collection(collection_id, validate_permissions, permission_error_message):
    if not collection_id:
        return None

    try:
        collection = Collection.objects.get(id=collection_id)
    except Collection.DoesNotExist:
        return Response(
            {"error": "Collection not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        validate_permissions([collection])
    except (DjangoPermissionDenied, DRFPermissionDenied):
        return Response(
            {"error": permission_error_message},
            status=status.HTTP_403_FORBIDDEN,
        )

    return collection


def extract_google_place_details(payload, fallback_query=""):
    place_id = str(payload.get("place_id") or "").strip() or None
    details = {}

    if not place_id:
        return place_id, details

    details_result = get_place_details(place_id, fallback_query=fallback_query)
    if isinstance(details_result, dict):
        if "error" not in details_result or details_result.get("description"):
            details = details_result

    return place_id, details


def preferred_link(payload, details):
    website = clean_url(details.get("website")) or clean_url(payload.get("website"))
    maps_url = clean_url(details.get("google_maps_url")) or clean_url(payload.get("google_maps_url"))
    return clean_url(payload.get("link")) or website or maps_url


def infer_lodging_type(primary_type, place_types):
    valid_types = {
        "hotel",
        "hostel",
        "resort",
        "bnb",
        "campground",
        "cabin",
        "apartment",
        "house",
        "villa",
        "motel",
        "other",
    }

    if isinstance(primary_type, str):
        normalized = primary_type.strip().lower()
        if normalized in valid_types:
            return normalized

    normalized_types = [
        str(type_name).strip().lower()
        for type_name in (place_types or [])
        if str(type_name).strip()
    ]

    mapping = {
        "hotel": "hotel",
        "resort_hotel": "resort",
        "motel": "motel",
        "hostel": "hostel",
        "bed_and_breakfast": "bnb",
        "guest_house": "bnb",
        "campground": "campground",
        "rv_park": "campground",
        "camping_cabin": "cabin",
        "apartment_building": "apartment",
        "lodging": "hotel",
        "villa": "villa",
    }

    for type_name in normalized_types:
        if type_name in mapping:
            return mapping[type_name]

    for type_name in normalized_types:
        if type_name in valid_types:
            return type_name

    return "other"
