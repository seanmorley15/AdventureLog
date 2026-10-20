"""
Date-keyed trips: reordering placements and generating them from dated records.

A day-based trip is planned with the rest of this package. These two operations are for
trips that still place records by calendar date rather than by day.
"""

from datetime import date, timedelta
from typing import List

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from pytz import timezone as pytz_timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from adventures.models import (
    Checklist, Collection, CollectionItineraryItem, Lodging, Note, Transportation, Visit,
)
from adventures.access.audience import can_edit


@transaction.atomic
def reorder_itinerary_items(request, items_data: List[dict]):
    """Reorder itinerary items in bulk.

    Args:
        request: the request, for permission checks (a guest link is identified by its cookie)
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

    # Permission checks: owner, editor, or guest editor
    for item_id in item_ids:
        item = items_map.get(item_id)
        if not item:
            continue

        collection = item.collection
        if not can_edit(request, collection):
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


def _datetime_to_date_in_timezone(dt, timezone_str: str | None) -> date:
    """
    Convert a datetime to a date, accounting for timezone only if there's actual time information.
    
    If the datetime is at UTC midnight (00:00:00), treat it as a date-only value and don't convert.
    If the datetime has a time component, apply timezone conversion.
    
    Args:
        dt: datetime object (can be timezone-aware or naive)
        timezone_str: IANA timezone string (e.g., 'America/New_York')
        
    Returns:
        date: The date in the specified timezone (or UTC if date-only)
    """
    if dt is None:
        return None
    
    # If it's already a date, return it
    if isinstance(dt, date) and not hasattr(dt, 'time'):
        return dt
    
    # Check if this is a date-only value (stored as UTC midnight)
    # If time is 00:00:00, treat it as date-only and don't apply timezone conversion
    if hasattr(dt, 'hour') and dt.hour == 0 and dt.minute == 0 and dt.second == 0:
        return dt.date() if hasattr(dt, 'date') else dt
    
    # Ensure datetime is timezone-aware (assume UTC if naive)
    if hasattr(dt, 'tzinfo') and dt.tzinfo is None:
        dt = timezone.make_aware(dt, timezone.utc)
    
    # Convert to target timezone if provided, otherwise use UTC
    if timezone_str:
        try:
            target_tz = pytz_timezone(timezone_str)
            dt = dt.astimezone(target_tz)
        except Exception:
            # If timezone conversion fails, use UTC
            pass
    
    return dt.date() if hasattr(dt, 'date') else dt
def auto_generate_itinerary(collection: Collection) -> List[CollectionItineraryItem]:
    """
    Auto-generate itinerary items for a collection based on dated records.
    
    Rules:
    - Visits: Create one item per day of the visit (spanning multiple days)
    - Lodging: Create one item on check_in date only
    - Transportation: Create one item on start date
    - Notes: Create one item on their date if present
    - Checklists: Create one item on their date if present
    
    Order within a day (incremental):
    1. Lodging (check-ins)
    2. Visits
    3. Transportation
    4. Notes
    5. Checklists
    
    Args:
        collection: Collection to generate itinerary for
        
    Returns:
        List[CollectionItineraryItem]: Created itinerary items
        
    Raises:
        ValidationError: If collection already has itinerary items or has no dated records
    """
    
    # Validation: collection must have zero itinerary items
    if collection.itinerary_items.exists():
        raise ValidationError({
            "detail": "Collection already has itinerary items. Cannot auto-generate."
        })
    
    # Get collection date range
    if not collection.start_date or not collection.end_date:
        raise ValidationError({
            "detail": "Collection must have start_date and end_date set."
        })
    
    start_date = collection.start_date
    end_date = collection.end_date
    
    # Collect all items to be added, grouped by date
    items_by_date = {}  # date -> [(content_type, object_id, priority)]
    
    # Priority order for sorting within a day
    PRIORITY_LODGING = 1
    PRIORITY_VISIT = 2
    PRIORITY_TRANSPORTATION = 3
    PRIORITY_NOTE = 4
    PRIORITY_CHECKLIST = 5
    
    # Process Visits: one location item per day of the visit
    # Note: We reference the Location, not the Visit itself
    from adventures.models import Location
    
    visits = Visit.objects.filter(location__collections=collection).select_related('location').distinct()
    for visit in visits:
        if visit.start_date and visit.location:
            # Convert to date using visit's timezone
            visit_start = _datetime_to_date_in_timezone(visit.start_date, visit.timezone)
            visit_end = _datetime_to_date_in_timezone(visit.end_date, visit.timezone) if visit.end_date else visit_start
            
            # Only include dates within collection range
            visit_start = max(visit_start, start_date)
            visit_end = min(visit_end or visit_start, end_date)
            
            current_date = visit_start
            while current_date <= visit_end:
                if current_date not in items_by_date:
                    items_by_date[current_date] = []
                items_by_date[current_date].append((
                    ContentType.objects.get_for_model(Location),
                    visit.location.id,  # Use Location ID, not Visit ID
                    PRIORITY_VISIT
                ))
                current_date += timedelta(days=1)
    
    # Process Lodging: one item on check_in date only
    lodgings = Lodging.objects.filter(collection=collection)
    for lodging in lodgings:
        if lodging.check_in:
            # Convert to date using lodging's timezone
            checkin_date = _datetime_to_date_in_timezone(lodging.check_in, lodging.timezone)
            
            # Only include if within collection range
            if start_date <= checkin_date <= end_date:
                if checkin_date not in items_by_date:
                    items_by_date[checkin_date] = []
                items_by_date[checkin_date].append((
                    ContentType.objects.get_for_model(Lodging),
                    lodging.id,
                    PRIORITY_LODGING
                ))
    
    # Process Transportation: one item on start date
    transportations = Transportation.objects.filter(collection=collection)
    for transportation in transportations:
        if transportation.date:
            # Convert to date using transportation's start timezone
            trans_date = _datetime_to_date_in_timezone(transportation.date, transportation.start_timezone)
            
            # Only include if within collection range
            if start_date <= trans_date <= end_date:
                if trans_date not in items_by_date:
                    items_by_date[trans_date] = []
                items_by_date[trans_date].append((
                    ContentType.objects.get_for_model(Transportation),
                    transportation.id,
                    PRIORITY_TRANSPORTATION
                ))
    
    # Process Notes: one item on their date
    notes = Note.objects.filter(collection=collection)
    for note in notes:
        if note.date:
            # Notes don't have timezone field, use UTC
            note_date = _datetime_to_date_in_timezone(note.date, None)
            
            # Only include if within collection range
            if start_date <= note_date <= end_date:
                if note_date not in items_by_date:
                    items_by_date[note_date] = []
                items_by_date[note_date].append((
                    ContentType.objects.get_for_model(Note),
                    note.id,
                    PRIORITY_NOTE
                ))
    
    # Process Checklists: one item on their date
    checklists = Checklist.objects.filter(collection=collection)
    for checklist in checklists:
        if checklist.date:
            # Checklists don't have timezone field, use UTC
            checklist_date = _datetime_to_date_in_timezone(checklist.date, None)
            
            # Only include if within collection range
            if start_date <= checklist_date <= end_date:
                if checklist_date not in items_by_date:
                    items_by_date[checklist_date] = []
                items_by_date[checklist_date].append((
                    ContentType.objects.get_for_model(Checklist),
                    checklist.id,
                    PRIORITY_CHECKLIST
                ))
    
    # Validation: must have at least one dated record
    if not items_by_date:
        raise ValidationError({
            "detail": "No dated records found within collection date range."
        })
    
    # Create itinerary items
    created_items = []
    
    for day_date in sorted(items_by_date.keys()):
        # Sort items by priority within the day
        items = sorted(items_by_date[day_date], key=lambda x: x[2])
        
        for order, (content_type, object_id, priority) in enumerate(items):
            itinerary_item = CollectionItineraryItem.objects.create(
                collection=collection,
                content_type=content_type,
                object_id=object_id,
                date=day_date,
                order=order
            )
            created_items.append(itinerary_item)
    
    return created_items
