from typing import List, Optional, Tuple
from django.db import transaction
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.exceptions import ValidationError, PermissionDenied
from adventures.models import CollectionItineraryItem, Visit, Lodging, Location


@transaction.atomic
def reorder_itinerary_items(user, items_data: List[dict]):
    """Reorder itinerary items in bulk.

    Args:
        user: requesting user (for permission checks)
        items_data: list of dicts with keys `id`, `date`, `order`

    Returns:
        List[CollectionItineraryItem]: updated items (unsaved instances are saved by this function)

    Raises:
        ValidationError, PermissionDenied
    """
    if not items_data:
        raise ValidationError({"items": "This field is required and must not be empty."})

    if not isinstance(items_data, list):
        raise ValidationError({"items": "Must be a list of item updates."})

    # Resolve ids and fetch items
    item_ids = [item.get('id') for item in items_data if item.get('id')]
    items_qs = CollectionItineraryItem.objects.filter(id__in=item_ids).select_related('collection')

    if items_qs.count() != len(item_ids):
        raise ValidationError({"items": "One or more items not found."})

    items_map = {str(it.id): it for it in items_qs}

    # Permission checks: user must be collection owner or in shared_with
    for item_id in item_ids:
        item = items_map.get(item_id)
        if not item:
            continue

        collection = item.collection
        if not (collection.user == user or collection.shared_with.filter(id=user.id).exists()):
            raise PermissionDenied("You do not have permission to modify items in this collection.")

    # Two-phase update to avoid unique constraint races:
    # 1) assign very large temporary order values (guaranteed > existing orders)
    # 2) assign final date/order values

    temp_offset = 1_000_000
    temp_updates = []
    for i, item_data in enumerate(items_data):
        item_id = item_data.get('id')
        if not item_id:
            continue
        item = items_map.get(item_id)
        if not item:
            continue
        item.order = temp_offset + i
        temp_updates.append(item)

    if temp_updates:
        CollectionItineraryItem.objects.bulk_update(temp_updates, ['order'])

    # Finalize
    updated_items = []
    for item_data in items_data:
        item_id = item_data.get('id')
        if not item_id:
            continue
        item = items_map.get(item_id)
        if not item:
            continue

        new_date = item_data.get('date')
        new_is_global = item_data.get('is_global')
        new_order = item_data.get('order')
        # If is_global is explicitly provided, set it and reconcile date accordingly
        if new_is_global is not None:
            item.is_global = bool(new_is_global)
            if item.is_global:
                item.date = None
        if (new_date is not None) and (not item.is_global):
            # validate date is within collection bounds (if collection has start/end)
            parsed = None
            try:
                parsed = parse_date(str(new_date))
            except Exception:
                parsed = None
            if parsed is None:
                try:
                    dt = parse_datetime(str(new_date))
                    if dt:
                        parsed = dt.date()
                except Exception:
                    parsed = None

            collection = item.collection
            if parsed and collection:
                if collection.start_date and parsed < collection.start_date:
                    raise ValidationError({"items": f"Item {item_id} date {parsed} is before collection start date {collection.start_date}."})
                if collection.end_date and parsed > collection.end_date:
                    raise ValidationError({"items": f"Item {item_id} date {parsed} is after collection end date {collection.end_date}."})

            item.date = new_date
        if new_order is not None:
            item.order = new_order

        updated_items.append(item)

    if updated_items:
        CollectionItineraryItem.objects.bulk_update(updated_items, ['date', 'is_global', 'order'])

    return updated_items


def resolve_item_coordinates(item: CollectionItineraryItem) -> Optional[Tuple[float, float]]:
    """Return (latitude, longitude) for an itinerary item that resolves to a
    single geographic point, or None if it doesn't.

    Content types behind `CollectionItineraryItem.item` (a GenericForeignKey)
    that resolve to a single point:
    - Visit -> its Location's latitude/longitude
    - Location -> its own latitude/longitude (the itinerary "+ Location"
      quick-add flow saves the item with content_type=Location directly —
      the Visit created alongside it, if any, is a separate object used for
      calendar display, not what's linked here)
    - Lodging -> its own latitude/longitude

    Transportation is a leg between two points (not a stop) and Note has no
    coordinates at all — both are deliberately excluded from route
    optimization rather than guessed at. Callers (routing endpoints) must
    treat items this returns None for as "not part of the optimizable set"
    and leave their `order`/`date` untouched, not drop them.
    """
    obj = item.item
    if obj is None:
        return None

    if isinstance(obj, Visit):
        location = obj.location
        if location and location.latitude is not None and location.longitude is not None:
            return (float(location.latitude), float(location.longitude))
        return None

    if isinstance(obj, Location):
        if obj.latitude is not None and obj.longitude is not None:
            return (float(obj.latitude), float(obj.longitude))
        return None

    if isinstance(obj, Lodging):
        if obj.latitude is not None and obj.longitude is not None:
            return (float(obj.latitude), float(obj.longitude))
        return None

    return None
