"""Multi-day spans and projecting a day plan's dates onto the records placed on it."""

from __future__ import annotations

import datetime


from .errors import DayPlanError
from .constants import SPAN_TYPES
from .dates import local_date, move_to_date, projected_date, shift_datetime
from .registry import indexed_days, item_kind


def sync_projection(collection, days=None):
    """Mirror projected dates onto days, items, and the derived end_date."""
    from adventures.models import CollectionItineraryDay, CollectionItineraryItem

    days = days if days is not None else indexed_days(collection)
    anchor = collection.start_date
    changed_days = []
    for day in days:
        new_date = projected_date(anchor, day.index)
        if day.date != new_date:
            day.date = new_date
            changed_days.append(day)
    if changed_days:
        CollectionItineraryDay.objects.bulk_update(changed_days, ['date'])

    date_by_day = {day.pk: day.date for day in days}
    items = list(CollectionItineraryItem.objects.filter(collection=collection, day__isnull=False))
    changed_items = []
    for item in items:
        new_date = date_by_day.get(item.day_id)
        if item.date != new_date:
            item.date = new_date
            changed_items.append(item)
    if changed_items:
        CollectionItineraryItem.objects.bulk_update(changed_items, ['date'])

    end_date = projected_date(anchor, len(days)) if days else collection.end_date
    if anchor is None:
        end_date = None
    if collection.end_date != end_date:
        collection.end_date = end_date
        collection.save(update_fields=['end_date', 'updated_at'])

def span_bounds(item, day_index=None):
    start = day_index if day_index is not None else (item.day.index if item.day_id else None)
    if start is None:
        return None, None
    end = item.span_end_index if item.span_end_index and item.span_end_index > start else start
    return start, end

def write_object_dates(item, anchor):
    """
    Write lodging or transport dates from a day placement.

    Lodging check-in is the start day and check-out is the morning after the
    span. Transport departs on the start day in ``start_timezone`` and arrives on
    the span end in ``end_timezone``. Without an anchor nothing is written.
    Returns the saved object, or None.
    """
    item_type = item_kind(item)
    if item_type not in SPAN_TYPES or anchor is None or not item.day_id:
        return None
    obj = item.item
    if obj is None:
        return None
    start_index, end_index = span_bounds(item)
    start_day = projected_date(anchor, start_index)
    end_day = projected_date(anchor, end_index)

    if item_type == 'lodging':
        check_in = move_to_date(obj.check_in, start_day, obj.timezone, item.start_time)
        check_out = move_to_date(
            obj.check_out, end_day + datetime.timedelta(days=1), obj.timezone, item.end_time
        )
        if obj.check_in == check_in and obj.check_out == check_out:
            return obj
        obj.check_in, obj.check_out = check_in, check_out
        obj.save(update_fields=['check_in', 'check_out', 'updated_at'])
        return obj

    arrival_zone = obj.end_timezone or obj.start_timezone
    if end_index == start_index and obj.date is not None and obj.end_date is not None:
        # An overnight leg on one day keeps its own day gap, read in each end's zone.
        gap = (local_date(obj.end_date, arrival_zone) - local_date(obj.date, obj.start_timezone)).days
        end_day = end_day + datetime.timedelta(days=max(gap, 0))
    departure = move_to_date(obj.date, start_day, obj.start_timezone, item.start_time)
    arrival = obj.end_date
    if obj.end_date is not None or end_index != start_index or item.end_time is not None:
        arrival = move_to_date(obj.end_date, end_day, arrival_zone, item.end_time)
        if arrival < departure:
            arrival = departure
    if obj.date == departure and obj.end_date == arrival:
        return obj
    obj.date, obj.end_date = departure, arrival
    obj.save(update_fields=['date', 'end_date', 'updated_at'])
    return obj

def clear_object_dates(item):
    item_type = item_kind(item)
    obj = item.item
    if obj is None or item_type not in SPAN_TYPES:
        return None
    if item_type == 'lodging':
        if obj.check_in is None and obj.check_out is None:
            return obj
        obj.check_in = None
        obj.check_out = None
        obj.save(update_fields=['check_in', 'check_out', 'updated_at'])
    else:
        if obj.date is None and obj.end_date is None:
            return obj
        obj.date = None
        obj.end_date = None
        obj.save(update_fields=['date', 'end_date', 'updated_at'])
    return obj

def shift_object_dates(item, days):
    """
    Shift lodging or transport clocks by ``days`` civil days in their own zones.

    Lodging moves in its timezone; transport departure in ``start_timezone`` and
    arrival in ``end_timezone``. Rows with no dates yet are filled from the day.
    """
    obj = item.item
    item_type = item_kind(item)
    if obj is None or item_type not in SPAN_TYPES or not days:
        return None
    if item_type == 'lodging':
        if obj.check_in is None and obj.check_out is None:
            return write_object_dates(item, item.collection.start_date)
        obj.check_in = shift_datetime(obj.check_in, days, obj.timezone)
        obj.check_out = shift_datetime(obj.check_out, days, obj.timezone)
        obj.save(update_fields=['check_in', 'check_out', 'updated_at'])
        return obj
    if obj.date is None and obj.end_date is None:
        return write_object_dates(item, item.collection.start_date)
    obj.date = shift_datetime(obj.date, days, obj.start_timezone)
    obj.end_date = shift_datetime(obj.end_date, days, obj.end_timezone or obj.start_timezone)
    obj.save(update_fields=['date', 'end_date', 'updated_at'])
    return obj

def shift_spans(collection, days):
    from adventures.models import CollectionItineraryItem

    updated = []
    items = CollectionItineraryItem.objects.filter(
        collection=collection, day__isnull=False
    ).select_related('day', 'content_type', 'collection')
    for item in items:
        obj = shift_object_dates(item, days)
        if obj is not None:
            updated.append(obj)
    return updated

def span_snapshot(collection):
    from adventures.models import CollectionItineraryItem

    snapshot = {}
    for item in CollectionItineraryItem.objects.filter(collection=collection, day__isnull=False).select_related('day', 'content_type'):
        if item_kind(item) in SPAN_TYPES:
            snapshot[item.pk] = span_bounds(item)
    return snapshot

def rewrite_changed_spans(collection, before, force=False):
    """Rewrite lodging and transport dates whose projected days changed."""
    from adventures.models import CollectionItineraryItem

    if collection.start_date is None:
        return []
    updated = []
    items = CollectionItineraryItem.objects.filter(collection=collection, day__isnull=False).select_related('day', 'content_type')
    for item in items:
        if item_kind(item) not in SPAN_TYPES:
            continue
        if force or before.get(item.pk) != span_bounds(item):
            obj = write_object_dates(item, collection.start_date)
            if obj is not None:
                updated.append(obj)
    return updated

def validate_span(item_type, day_index, span_end_index, count):
    if span_end_index is None:
        return None
    try:
        span_end_index = int(span_end_index)
    except (TypeError, ValueError):
        raise DayPlanError('span_end_index must be a day number.')
    if item_type not in SPAN_TYPES and item_type != 'location':
        raise DayPlanError('Only lodging, transport, and locations can span days.')
    if day_index is None:
        raise DayPlanError('Only placements on a day can span days.')
    if span_end_index < day_index or span_end_index > count:
        raise DayPlanError('The span must end on a day of this trip, on or after its start.')
    return span_end_index if span_end_index > day_index else None
