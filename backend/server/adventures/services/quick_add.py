"""Quick add: creating a place or lodging from a map pin or search result in one call.

This module reads the request payload, looks up the place's details and address, and works out
what to create. The views create the record (they own who may add to which collection) and then
call ``finish_quick_add``. Anything the caller did wrong raises ``QuickAddError``.
"""

import datetime
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.dateparse import parse_date, parse_datetime

from adventures.models import Category, Collection, CollectionItineraryDay, CollectionItineraryItem, ContentImage
from adventures.services import day_plan
from adventures.services.geocoding.reverse import reverse_geocode as reverse_geocode_service
from adventures.services.images.fetch import import_remote_images_for_object
from adventures.services.places.details import get_place_details
from core.dates import aware_utc_from_date
from core.errors import ServiceError
from core.parsing import (
    clean_url,
    coerce_bool,
    coerce_coordinate,
    coerce_float,
    sanitize_photo_urls,
    sanitize_tags,
)


class QuickAddError(ServiceError):
    """A quick add that cannot proceed, with the HTTP status the caller should answer with."""

    _CODES = {403: 'permission_denied', 404: 'not_found'}

    def __init__(self, message, status_code=400):
        super().__init__(message, code=self._CODES.get(status_code, 'invalid'), status=status_code)
        self.status_code = status_code


@dataclass
class QuickAdd:
    """Everything worked out before the record exists."""

    serializer_payload: Dict[str, Any]
    collection: Optional[Collection]
    reverse_data: Dict[str, Any] = field(default_factory=dict)
    location_label: Optional[str] = None
    itinerary_date: Optional[datetime.date] = None


def build_quick_add_description(base_description, detailed_description):
    description = str(detailed_description or "").strip() or str(base_description or "").strip()
    return description or None


def resolve_quick_add_location_label(payload, reverse_data, details):
    """Prefer server reverse-geocoded display_name over raw provider address strings."""
    reverse_data = reverse_data if isinstance(reverse_data, dict) else {}
    details = details if isinstance(details, dict) else {}
    payload = payload if isinstance(payload, dict) else {}

    return (
        str(reverse_data.get('display_name') or '').strip()
        or str(payload.get('location') or '').strip()
        or str(details.get('formatted_address') or '').strip()
        or None
    )


def resolve_quick_add_collection(collection_id, can_add: Callable[[Collection], bool], permission_error_message):
    if not collection_id:
        return None

    try:
        collection = Collection.objects.get(id=collection_id)
    except (Collection.DoesNotExist, ValueError, ValidationError):
        raise QuickAddError('Collection not found.', 404)

    if not can_add(collection):
        raise QuickAddError(permission_error_message, 403)
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
        raise QuickAddError('Itinerary item date is before the collection start_date')
    if collection.end_date and date_value > collection.end_date:
        raise QuickAddError('Itinerary item date is after the collection end_date')


def apply_quick_add_itinerary_date(content_object, date_value):
    """Date-keyed trips: give undated lodging that day. Locations never get a visit."""
    if not content_object or not date_value:
        return

    if content_object._meta.model_name == "lodging":
        if content_object.check_in and content_object.check_out:
            return

        check_in = aware_utc_from_date(date_value)
        check_out = check_in + datetime.timedelta(days=1)
        content_object.check_in = check_in
        content_object.check_out = check_out
        content_object.save(update_fields=["check_in", "check_out"])


def create_quick_add_itinerary_item(collection, content_object, date_value):
    if not collection or not content_object or not date_value:
        return None

    validate_itinerary_date(collection, date_value)

    content_type = ContentType.objects.get_for_model(content_object.__class__)

    if day_plan.is_day_based(collection):
        day = CollectionItineraryDay.objects.filter(
            collection=collection, index__isnull=False, date=date_value
        ).first()
        if day is None:
            raise QuickAddError('That date is not a day of this trip.')
        existing_item = CollectionItineraryItem.objects.filter(
            collection=collection, content_type=content_type, object_id=content_object.id, day=day
        ).first()
        if existing_item:
            return existing_item
        item, _ = day_plan.place_object(collection, content_type, content_object.id, day=day)
        return item

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
            collection=collection, date=date_value, is_global=False, day__isnull=True
        ).aggregate(max_order=models.Max("order"))["max_order"]
    )
    if max_order is None:
        max_order = -1

    apply_quick_add_itinerary_date(content_object, date_value)

    return CollectionItineraryItem.objects.create(
        collection=collection,
        content_type=content_type,
        object_id=content_object.id,
        date=date_value,
        is_global=False,
        order=max_order + 1,
    )


def import_quick_add_photos(content_object, payload):
    """Download the photos a quick add came with. Returns the import summary, or None when there are none."""
    photo_urls = sanitize_photo_urls(payload.get('photos'))
    if not photo_urls:
        return None
    return import_remote_images_for_object(
        content_object,
        photo_urls,
        owner=content_object.user,
        max_workers=min(5, len(photo_urls)),
        explicit_source=ContentImage.Source.GOOGLE,
    )


def read_quick_add_basics(payload):
    """The name and coordinates every quick add needs."""
    name = str(payload.get('name') or '').strip()
    if not name:
        raise QuickAddError('name is required')

    latitude = coerce_coordinate(payload.get('latitude'), -90, 90)
    longitude = coerce_coordinate(payload.get('longitude'), -180, 180)
    if latitude is None or longitude is None:
        raise QuickAddError('Valid latitude and longitude are required')
    return name, latitude, longitude


def lookup_reverse_geocode(user, latitude, longitude):
    """The address data for a point, or an empty dict when it cannot be found."""
    try:
        selection = reverse_geocode_service(latitude, longitude, user)
        if selection and selection.data and not selection.data.get('error'):
            return selection.data
    except Exception:
        pass
    return {}


def normalize_quick_add_category(raw_category, user):
    """The category a quick add names, as fields to create it from, or None. Raises when it cannot be used."""
    if not raw_category:
        return None

    if isinstance(raw_category, dict):
        category_id = str(raw_category.get('id') or '').strip()
        name = str(raw_category.get('name') or '').strip().lower()
        display_name = str(raw_category.get('display_name') or '').strip()
        icon = str(raw_category.get('icon') or '').strip() or '🌍'
    elif isinstance(raw_category, str):
        category_id = raw_category.strip()
        name = ''
        display_name = ''
        icon = '🌍'
    else:
        raise QuickAddError('category must be an object or string')

    category = None
    if category_id:
        try:
            category = Category.objects.filter(id=category_id, user=user).first()
        except (ValidationError, ValueError, TypeError):
            category = None

    if category:
        return {'name': category.name, 'display_name': category.display_name, 'icon': category.icon}

    # New categories from the dropdown are assigned a client-side id that does not exist yet.
    # Fall through to create-by-name, matching LocationSerializer.get_or_create_category.
    if not name:
        if category_id:
            raise QuickAddError('Category not found or inaccessible')
        return None

    return {'name': name, 'display_name': display_name or name, 'icon': icon}


def prepare_location_quick_add(user, payload, can_add_to_collection):
    """Work out the place to create from a quick-add payload. Creates nothing."""
    name, latitude, longitude = read_quick_add_basics(payload)
    collection = resolve_quick_add_collection(
        payload.get('collection'),
        can_add_to_collection,
        'You do not have permission to add this location to the selected collection.',
    )

    try:
        _, details = extract_google_place_details(payload, fallback_query=name)
    except Exception:
        details = {}
    reverse_data = lookup_reverse_geocode(user, latitude, longitude)

    rating = coerce_float(payload.get('rating'))
    if rating is None:
        rating = coerce_float(details.get('rating'))
    location_label = resolve_quick_add_location_label(payload, reverse_data, details)
    category = normalize_quick_add_category(payload.get('category'), user)

    serializer_payload = {
        'name': name,
        'location': location_label,
        'latitude': latitude,
        'longitude': longitude,
        'rating': rating,
        'description': build_quick_add_description(
            base_description=payload.get('description'),
            detailed_description=details.get('description'),
        ),
        'link': preferred_link(payload, details),
        'tags': sanitize_tags(payload.get('types') or payload.get('tags')),
        'is_public': coerce_bool(payload.get('is_public'), default=False),
    }
    if category:
        serializer_payload['category'] = category
    if collection:
        serializer_payload['collections'] = [str(collection.id)]

    return QuickAdd(
        serializer_payload=serializer_payload,
        collection=collection,
        reverse_data=reverse_data,
        location_label=location_label,
        itinerary_date=parse_itinerary_date(payload.get('itinerary_date')),
    )


def prepare_lodging_quick_add(user, payload, can_add_to_collection):
    """Work out the lodging to create from a quick-add payload. Creates nothing."""
    name, latitude, longitude = read_quick_add_basics(payload)
    collection = resolve_quick_add_collection(
        payload.get('collection'),
        can_add_to_collection,
        'You do not have permission to add this lodging to the selected collection.',
    )

    reverse_data = lookup_reverse_geocode(user, latitude, longitude)
    _, details = extract_google_place_details(payload, fallback_query=name)

    rating = coerce_float(payload.get('rating'))
    if rating is None:
        rating = coerce_float(details.get('rating'))
    location_label = resolve_quick_add_location_label(payload, reverse_data, details)

    place_types = payload.get('types')
    if not isinstance(place_types, list) or not place_types:
        place_types = details.get('types') if isinstance(details.get('types'), list) else []

    serializer_payload = {
        'name': name,
        'type': infer_lodging_type(payload.get('type'), place_types),
        'location': location_label,
        'latitude': latitude,
        'longitude': longitude,
        'rating': rating,
        'description': build_quick_add_description(
            base_description=payload.get('description'),
            detailed_description=details.get('description'),
        ),
        'link': preferred_link(payload, details),
        'is_public': coerce_bool(payload.get('is_public'), default=False),
    }
    if collection:
        serializer_payload['collection'] = str(collection.id)

    return QuickAdd(
        serializer_payload=serializer_payload,
        collection=collection,
        reverse_data=reverse_data,
        location_label=location_label,
        itinerary_date=parse_itinerary_date(payload.get('itinerary_date')),
    )


def finish_quick_add(content_object, prepared, payload):
    """Place the new record on its day and download its photos. Returns (placement, photo import summary)."""
    itinerary_item = None
    if prepared.collection and prepared.itinerary_date:
        itinerary_item = create_quick_add_itinerary_item(
            prepared.collection, content_object, prepared.itinerary_date
        )
    return itinerary_item, import_quick_add_photos(content_object, payload)
