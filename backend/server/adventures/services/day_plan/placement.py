"""Putting records on days and moving them around."""

from __future__ import annotations


from django.db import transaction

from .errors import DayPlanError
from .constants import GLOBAL_TYPES, PLACEABLE_TYPES, TEMP_ORDER_OFFSET
from .registry import day_count, indexed_days, item_kind, require_day_based
from .ordering import compact_bucket, lock, next_order, reorder_bucket
from .spans import clear_object_dates, span_bounds, validate_span, write_object_dates


def place_object(collection, content_type, object_id, *, day=None, is_global=False, order=None,
                 span_end_index=None, is_optional=False, start_time=None, end_time=None, timezone_name=None):
    """
    Place an object on a day, in Ideas, or trip-wide.

    Locations may be placed more than once. Lodging, transport, notes, and
    checklists have one placement; placing again moves the existing row.
    Lodging and transport dates are written in the same transaction.
    """
    from adventures.models import CollectionItineraryItem

    item_type = content_type.model
    if item_type not in PLACEABLE_TYPES:
        raise DayPlanError(f'{item_type} cannot be placed on a day plan.')
    if is_global and item_type not in GLOBAL_TYPES:
        raise DayPlanError('Only notes and checklists can be trip-wide.')
    if is_global and day is not None:
        raise DayPlanError('Trip-wide items do not sit on a day.')

    with transaction.atomic():
        collection = lock(collection)
        if day is None and not is_global:
            on_a_day = CollectionItineraryItem.objects.filter(
                collection=collection,
                content_type=content_type,
                object_id=object_id,
                day__isnull=False,
            ).exists()
            if on_a_day:
                raise DayPlanError(
                    'This is already on a day, so it stays on the plan.',
                    code='already_planned',
                )
        count = day_count(collection)
        span_end_index = validate_span(item_type, day.index if day else None, span_end_index, count)

        existing = None
        if item_type != 'location':
            existing = CollectionItineraryItem.objects.filter(
                collection=collection, content_type=content_type, object_id=object_id
            ).order_by('created_at').first()

        if existing is not None:
            move_placement(
                collection,
                existing,
                day=day,
                is_global=is_global,
                order=order,
                span_end_index=span_end_index,
                span_given=True,
            )
            existing.refresh_from_db()
            changes = {}
            if is_optional != existing.is_optional:
                changes['is_optional'] = is_optional
            if start_time is not None:
                changes['start_time'] = start_time
            if end_time is not None:
                changes['end_time'] = end_time
            if timezone_name:
                changes['timezone'] = timezone_name
            if changes:
                for key, value in changes.items():
                    setattr(existing, key, value)
                existing.save(update_fields=list(changes) + ['updated_at'])
            return existing, False

        target_order = next_order(collection, day=day, is_global=is_global)
        item = CollectionItineraryItem.objects.create(
            collection=collection,
            content_type=content_type,
            object_id=object_id,
            day=day,
            date=day.date if day else None,
            is_global=is_global,
            order=target_order,
            span_end_index=span_end_index,
            is_optional=bool(is_optional),
            start_time=start_time,
            end_time=end_time,
            timezone=timezone_name or None,
        )
        if order is not None:
            reorder_bucket(collection, item, int(order))
        if day is not None:
            write_object_dates(item, collection.start_date)
        elif not is_global:
            clear_object_dates(item)
        return item, True

def move_placement(collection, item, *, day=None, is_global=False, order=None, span_end_index=None, span_given=False):
    """Move one placement and write or clear lodging and transport dates with it."""
    from adventures.models import CollectionItineraryItem

    item_type = item_kind(item)
    if is_global and item_type not in GLOBAL_TYPES:
        raise DayPlanError('Only notes and checklists can be trip-wide.')

    with transaction.atomic():
        collection = lock(collection)
        count = day_count(collection)
        if span_given:
            span_end_index = validate_span(item_type, day.index if day else None, span_end_index, count)
        elif day is not None and item.span_end_index and item.day_id:
            length = item.span_end_index - item.day.index
            span_end_index = min(day.index + length, count) if length > 0 else None
            if span_end_index is not None and span_end_index <= day.index:
                span_end_index = None
        else:
            span_end_index = None

        old_bucket = (item.day_id, item.is_global)
        item.order = TEMP_ORDER_OFFSET * 3
        CollectionItineraryItem.objects.filter(pk=item.pk).update(order=item.order)

        item.day = day
        item.date = day.date if day else None
        item.is_global = bool(is_global)
        item.span_end_index = span_end_index
        item.order = next_order(collection, day=day, is_global=item.is_global)
        item.save(update_fields=['day', 'date', 'is_global', 'span_end_index', 'order', 'updated_at'])

        if order is not None:
            reorder_bucket(collection, item, int(order))
        compact_bucket(collection, *old_bucket)

        if day is not None:
            write_object_dates(item, collection.start_date)
        elif not is_global:
            clear_object_dates(item)
        return item

def reorder_day_plan(collection, entries):
    """
    Apply a batch of placements in one transaction.

    Each entry is ``{"id", "day_index" | None, "is_global", "order", "span_end_index"?}``.
    Lodging and transport dates move in the same transaction.
    """
    from adventures.models import CollectionItineraryItem

    with transaction.atomic():
        collection = lock(collection)
        require_day_based(collection)
        days = {day.index: day for day in indexed_days(collection)}
        count = len(days)
        ids = [entry.get('id') for entry in entries]
        items = {
            str(item.pk): item
            for item in CollectionItineraryItem.objects.filter(collection=collection, pk__in=ids).select_related('day', 'content_type')
        }
        if len(items) != len(set(ids)):
            raise DayPlanError('Some itinerary items were not found in this trip.', code='not_found')

        before = {pk: (item.day_id, item.is_global, span_bounds(item)) for pk, item in items.items()}

        ordered = list(items.values())
        for offset, item in enumerate(ordered):
            item.order = TEMP_ORDER_OFFSET + offset
        CollectionItineraryItem.objects.bulk_update(ordered, ['order'])

        for entry in entries:
            item = items[str(entry['id'])]
            item_type = item_kind(item)
            is_global = bool(entry.get('is_global', False))
            day_index = entry.get('day_index')
            day = None
            if is_global:
                if item_type not in GLOBAL_TYPES:
                    raise DayPlanError('Only notes and checklists can be trip-wide.')
            elif day_index is not None:
                day = days.get(int(day_index))
                if day is None:
                    raise DayPlanError(f'Day {day_index} is not part of this trip.')
            if 'span_end_index' in entry:
                span = validate_span(item_type, day.index if day else None, entry.get('span_end_index'), count)
            elif day is not None and item.span_end_index and item.day_id:
                length = item.span_end_index - item.day.index
                span = min(day.index + length, count) if length > 0 else None
                span = span if span and span > day.index else None
            else:
                span = None
            item.day = day
            item.date = day.date if day else None
            item.is_global = is_global
            item.span_end_index = span
            item.order = int(entry.get('order', 0))

        CollectionItineraryItem.objects.bulk_update(ordered, ['day', 'date', 'is_global', 'span_end_index', 'order'])

        updated_objects = []
        for pk, item in items.items():
            old_day, old_global, old_span = before[pk]
            if item.day_id is not None:
                if (old_day, old_global, old_span) != (item.day_id, item.is_global, span_bounds(item)):
                    obj = write_object_dates(item, collection.start_date)
                    if obj is not None:
                        updated_objects.append(obj)
            elif not item.is_global and old_day is not None:
                obj = clear_object_dates(item)
                if obj is not None:
                    updated_objects.append(obj)

        touched = {(b[0], b[1]) for b in before.values()} | {(i.day_id, i.is_global) for i in ordered}
        for day_id, is_global in touched:
            compact_bucket(collection, day_id, is_global)
        return [items[str(entry['id'])] for entry in entries], updated_objects
