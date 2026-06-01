import datetime
from urllib.parse import urlparse

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.db import models
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import status
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
from rest_framework.response import Response

from django.contrib.contenttypes.models import ContentType

from adventures.geocoding import get_place_details
from adventures.models import Collection, CollectionItineraryItem, Visit


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


def parse_itinerary_date(value):
    if not value:
        return None

    raw_value = str(value).strip()
    if not raw_value:
        return None

    parsed_date = parse_date(raw_value)
    if parsed_date:
        return parsed_date

    parsed_datetime = parse_datetime(raw_value)
    if parsed_datetime:
        return parsed_datetime.date()

    return None


def validate_itinerary_date(collection, date_value):
    if not collection or not date_value:
        return None

    if collection.start_date and date_value < collection.start_date:
        return Response(
            {"error": "Itinerary item date is before the collection start_date"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if collection.end_date and date_value > collection.end_date:
        return Response(
            {"error": "Itinerary item date is after the collection end_date"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return None


def apply_quick_add_itinerary_date(content_object, date_value):
    if not content_object or not date_value:
        return

    model_name = content_object._meta.model_name

    if model_name == "location":
        start_dt = datetime.datetime.combine(date_value, datetime.time.min)
        end_dt = datetime.datetime.combine(date_value, datetime.time.max)

        exact_match = Visit.objects.filter(
            location=content_object, start_date=start_dt, end_date=end_dt
        ).first()
        if exact_match:
            return

        overlap_q = models.Q(start_date__lte=end_dt) & models.Q(end_date__gte=start_dt)
        existing = Visit.objects.filter(location=content_object).filter(overlap_q).first()
        if existing:
            existing.start_date = start_dt
            existing.end_date = end_dt
            existing.save(update_fields=["start_date", "end_date"])
            return

        Visit.objects.create(
            location=content_object,
            start_date=start_dt,
            end_date=end_dt,
            notes="Created from quick add",
        )
        return

    if model_name == "lodging":
        if content_object.check_in and content_object.check_out:
            return

        check_in = datetime.datetime.combine(date_value, datetime.time.min)
        check_out = check_in + datetime.timedelta(days=1)
        content_object.check_in = check_in
        content_object.check_out = check_out
        content_object.save(update_fields=["check_in", "check_out"])


def create_quick_add_itinerary_item(collection, content_object, date_value):
    if not collection or not content_object or not date_value:
        return None

    existing_error = validate_itinerary_date(collection, date_value)
    if isinstance(existing_error, Response):
        return existing_error

    content_type = ContentType.objects.get_for_model(content_object.__class__)
    existing_item = CollectionItineraryItem.objects.filter(
        collection=collection,
        content_type=content_type,
        object_id=content_object.id,
        date=date_value,
        is_global=False,
    ).first()
    if existing_item:
        return existing_item

    max_order = (
        CollectionItineraryItem.objects.filter(
            collection=collection, date=date_value, is_global=False
        ).aggregate(max_order=models.Max("order"))["max_order"]
        or -1
    )

    apply_quick_add_itinerary_date(content_object, date_value)

    return CollectionItineraryItem.objects.create(
        collection=collection,
        content_type=content_type,
        object_id=content_object.id,
        date=date_value,
        is_global=False,
        order=max_order + 1,
    )
