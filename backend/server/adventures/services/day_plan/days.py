"""Operations on the days themselves: insert, duplicate, move, delete, length, and anchor."""

from __future__ import annotations

import datetime

from django.db import transaction

from .errors import DayPlanError
from .constants import SPAN_TYPES, TEMP_ORDER_OFFSET
from .registry import get_day, has_legacy_dated_items, indexed_days, is_day_based, item_kind, require_day_based
from .ordering import day_blocking_items, lock, next_order, place_after_existing, renumber, save_spans, spanning_items
from .spans import clear_object_dates, rewrite_changed_spans, shift_spans, span_snapshot, sync_projection
from .conversion import build_days


def insert_day(collection, position=None, name=None, description=None):
    """Insert an empty day before ``position`` (1-based); default appends."""
    from adventures.models import CollectionItineraryDay

    with transaction.atomic():
        collection = lock(collection)
        if not is_day_based(collection):
            if collection.type != 'trip' or has_legacy_dated_items(collection):
                raise DayPlanError('This trip is not planned by days yet.', code='not_day_based')
            if position not in (None, 1):
                raise DayPlanError('Position is outside the trip.')
            CollectionItineraryDay.objects.create(
                collection=collection,
                index=1,
                name=name or None,
                description=description or None,
            )
            sync_projection(collection)
            return collection
        days = indexed_days(collection)
        count = len(days)
        position = count + 1 if position is None else int(position)
        if position < 1 or position > count + 1:
            raise DayPlanError('Position is outside the trip.')
        before = span_snapshot(collection)
        from .files import extend_trail_spans

        extend_trail_spans(collection, position)

        spans = spanning_items(collection)
        for item in spans:
            start, end = item.day.index, item.span_end_index
            if start < position <= end:
                item.span_end_index = end + 1
            elif position <= start:
                item.span_end_index = end + 1

        new_day = CollectionItineraryDay.objects.create(
            collection=collection,
            index=TEMP_ORDER_OFFSET * 2,
            name=name or None,
            description=description or None,
        )
        days.insert(position - 1, new_day)
        renumber(days)
        for item in spans:
            item.day = next(d for d in days if d.pk == item.day_id)
        save_spans(spans)
        sync_projection(collection, days)
        rewrite_changed_spans(collection, before)
        return new_day

def duplicate_day(collection, day_id):
    """Insert a copy of a day after it, with its location, note, and checklist stops."""
    from adventures.models import CollectionItineraryItem

    with transaction.atomic():
        collection = lock(collection)
        require_day_based(collection)
        source = get_day(collection, day_id)
        new_day = insert_day(collection, source.index + 1, source.name, source.description)
        source_items = CollectionItineraryItem.objects.filter(collection=collection, day=source).select_related('content_type').order_by('order')
        order = 0
        for item in source_items:
            if item_kind(item) in SPAN_TYPES:
                continue
            CollectionItineraryItem.objects.create(
                collection=collection,
                content_type=item.content_type,
                object_id=item.object_id,
                day=new_day,
                date=new_day.date,
                order=order,
                is_optional=item.is_optional,
                start_time=item.start_time,
                end_time=item.end_time,
                timezone=item.timezone,
            )
            order += 1
        return new_day

def move_day(collection, day_id, position):
    """Move a day to ``position``; its stops and span starts move with it."""
    with transaction.atomic():
        collection = lock(collection)
        require_day_based(collection)
        days = indexed_days(collection)
        day = get_day(collection, day_id)
        position = int(position)
        if position < 1 or position > len(days):
            raise DayPlanError('Position is outside the trip.')
        before = span_snapshot(collection)
        from .files import retarget_trail_spans, trail_span_lengths

        trail_lengths = trail_span_lengths(collection)
        spans = spanning_items(collection)
        lengths = {item.pk: item.span_end_index - item.day.index for item in spans}

        days = [d for d in days if d.pk != day.pk]
        days.insert(position - 1, day)
        renumber(days)
        by_pk = {d.pk: d for d in days}
        for item in spans:
            item.day = by_pk[item.day_id]
            item.span_end_index = min(item.day.index + lengths[item.pk], len(days))
        save_spans(spans)
        retarget_trail_spans(trail_lengths, by_pk, len(days))
        sync_projection(collection, days)
        rewrite_changed_spans(collection, before)
        return by_pk[day.pk]

def delete_day(collection, day_id, destination=None, target_day_id=None):
    """
    Delete a day. Indexes stay contiguous and spans shrink around it.

    A day with stops needs ``destination``: ``ideas``, or ``day`` with
    ``target_day_id``. A span that starts on this day moves to the next day.
    """
    from adventures.models import CollectionItineraryItem

    with transaction.atomic():
        collection = lock(collection)
        require_day_based(collection)
        days = indexed_days(collection)
        day = get_day(collection, day_id)
        if len(days) <= 1:
            raise DayPlanError('A trip needs at least one day.')
        from .files import blocking_file_count, move_blocking_files, shrink_trail_spans

        blocking = day_blocking_items(collection, day)
        file_count = blocking_file_count(day)
        target_day = None
        if blocking or file_count:
            if destination not in ('day', 'ideas'):
                raise DayPlanError(
                    'This day has stops. Choose where they go.',
                    code='destination_required',
                    extra={'item_count': len(blocking) + file_count},
                )
            if destination == 'day':
                target_day = get_day(collection, target_day_id)
                if target_day.pk == day.pk:
                    raise DayPlanError('Choose a different day for these stops.')

        before = span_snapshot(collection)
        removed = day.index
        remaining = [d for d in days if d.pk != day.pk]
        next_day = next((d for d in remaining if d.index == removed + 1), None)

        def new_index(old):
            return old if old < removed else old - 1

        spans = spanning_items(collection)
        moved_starts = []
        for item in spans:
            start, end = item.day.index, item.span_end_index
            if start == removed:
                moved_starts.append(item)
                new_start = removed
            else:
                new_start = new_index(start)
            new_end = end - 1 if end >= removed else end
            item.span_end_index = new_end if new_end > new_start else None
        if spans:
            CollectionItineraryItem.objects.bulk_update(spans, ['span_end_index'])
        if moved_starts:
            place_after_existing(collection, next_day, moved_starts)
        shrink_trail_spans(collection, removed, next_day)

        ideas_moves = []
        if blocking:
            for item in blocking:
                item.span_end_index = None
            CollectionItineraryItem.objects.bulk_update(blocking, ['span_end_index'])
            if destination == 'day':
                place_after_existing(collection, target_day, blocking)
            else:
                order = next_order(collection)
                for offset, item in enumerate(blocking):
                    item.order = TEMP_ORDER_OFFSET + offset
                CollectionItineraryItem.objects.bulk_update(blocking, ['order'])
                for offset, item in enumerate(blocking):
                    item.day = None
                    item.date = None
                    item.order = order + offset
                    ideas_moves.append(item)
                CollectionItineraryItem.objects.bulk_update(blocking, ['day', 'date', 'order'])
        if file_count:
            move_blocking_files(day, destination, target_day, collection)

        day.delete()
        renumber(remaining)
        sync_projection(collection, remaining)
        for item in ideas_moves:
            clear_object_dates(item)
        rewrite_changed_spans(collection, before)

def set_duration(collection, count, anchor=..., destination=None, target_day_id=None, timezone_name=None):
    """
    Set the day count and, optionally, the anchor.

    Adding days appends empty days. Shortening removes trailing days; a trailing
    day with stops needs ``destination`` the same way delete does. ``anchor`` is
    a date or None; omit it to keep the current anchor.
    """
    with transaction.atomic():
        collection = lock(collection)
        if not is_day_based(collection):
            if collection.type != 'trip' or has_legacy_dated_items(collection):
                raise DayPlanError('This trip is not planned by days yet.', code='not_day_based')
            build_days(collection, int(count))
            collection.refresh_from_db()
            if anchor is not ...:
                set_anchor(collection, anchor, timezone_name=timezone_name)
            return collection
        try:
            count = int(count)
        except (TypeError, ValueError):
            raise DayPlanError('Day count must be a whole number.')
        if count < 1:
            raise DayPlanError('A trip needs at least one day.')

        days = indexed_days(collection)
        current = len(days)
        if count < current:
            from .files import blocking_file_count

            trailing = days[count:]
            blocked = [d for d in trailing if day_blocking_items(collection, d) or blocking_file_count(d)]
            if blocked and destination not in ('day', 'ideas'):
                raise DayPlanError(
                    'The days being removed have stops. Choose where they go.',
                    code='destination_required',
                    extra={'day_indexes': [d.index for d in blocked]},
                )
            if destination == 'day':
                target = get_day(collection, target_day_id)
                if target.index > count:
                    raise DayPlanError('Choose a day that is kept.')
            for day in reversed(trailing):
                delete_day(collection, day.pk, destination=destination, target_day_id=target_day_id)
        elif count > current:
            for _ in range(count - current):
                insert_day(collection)

        collection.refresh_from_db()
        if anchor is not ...:
            set_anchor(collection, anchor, timezone_name=timezone_name)
        else:
            sync_projection(collection)
        collection.refresh_from_db()
        return collection

def set_anchor(collection, anchor, timezone_name=None):
    """Set or clear the anchor and fill every lodging and transport date from its day."""
    with transaction.atomic():
        collection = lock(collection)
        require_day_based(collection)
        fields = []
        previous = collection.start_date
        if collection.start_date != anchor:
            collection.start_date = anchor
            fields.append('start_date')
        if timezone_name:
            from core.timezones import validate_timezone
            from django.core.exceptions import ValidationError as DjangoValidationError

            try:
                validate_timezone(timezone_name)
            except DjangoValidationError:
                raise DayPlanError(f'Unknown timezone: {timezone_name}')
            if collection.timezone != timezone_name:
                collection.timezone = timezone_name
                fields.append('timezone')
        if fields:
            collection.save(update_fields=fields + ['updated_at'])
        sync_projection(collection)
        if 'start_date' in fields:
            if previous is not None and anchor is not None:
                # Moving an existing anchor is a shift: clocks keep their faces.
                shift_spans(collection, (anchor - previous).days)
            else:
                rewrite_changed_spans(collection, {}, force=True)
        return collection

def shift_anchor(collection, days=None, start_date=None):
    """
    Move an anchored trip by a civil-day delta, or to a new ``start_date``.

    Day indexes, order, and spans stay. Lodging and transport clocks move with
    their days in their own timezones. Visits are not touched. This never runs
    the out-of-range cleanup that a collection PATCH runs.
    """
    with transaction.atomic():
        collection = lock(collection)
        require_day_based(collection)
        if collection.start_date is None:
            raise DayPlanError('Set a start date before shifting the trip.', code='no_anchor')
        if start_date is not None:
            days = (start_date - collection.start_date).days
        try:
            days = int(days)
        except (TypeError, ValueError):
            raise DayPlanError('Send a whole number of days or a start date.')
        if days == 0:
            return collection
        collection.start_date = collection.start_date + datetime.timedelta(days=days)
        collection.save(update_fields=['start_date', 'updated_at'])
        sync_projection(collection)
        shift_spans(collection, days)
        return collection
