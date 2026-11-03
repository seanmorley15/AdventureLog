"""Building a collection's day plan, from its dates or from scratch."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

from django.db import transaction

from .errors import DayPlanError
from .constants import TEMP_ORDER_OFFSET, TYPE_PRIORITY
from .dates import contiguous_runs, inclusive_span, local_date, projected_date
from .registry import Registry, is_day_based
from .ordering import next_order
from .spans import sync_projection


@dataclass
class _Target:
    bucket: str  # 'day' | 'ideas' | 'global'
    start: int | None = None
    end: int | None = None
    rank: tuple = field(default_factory=tuple)

def convert_collection(collection, apps=None) -> bool:
    """
    Convert a date-keyed trip into a day plan covering every date it spans.

    Idempotent: a collection that already has day indexes, a folder, or a trip
    without a positive date span is left unchanged. Returns True when days
    were built.
    """
    reg = Registry(apps)
    if collection.type != 'trip':
        return False
    if is_day_based(collection, reg):
        return False
    span = inclusive_span(collection.start_date, collection.end_date)
    if span is None or span < 1:
        return False
    with transaction.atomic():
        _build_day_plan(collection, span, reg)
    return True

def plan_by_days(collection, count=None):
    """Build a day plan from the anchor. ``count`` defaults to the date span."""
    reg = Registry()
    if collection.type != 'trip':
        raise DayPlanError('Only trips can be planned by days.')
    if is_day_based(collection, reg):
        raise DayPlanError('This trip is already planned by days.', code='conflict')
    if count is None:
        count = inclusive_span(collection.start_date, collection.end_date)
    if not isinstance(count, int) or count < 1:
        raise DayPlanError('Day count must be at least 1.')
    with transaction.atomic():
        _build_day_plan(collection, count, reg)
        if collection.start_date:
            collection.end_date = projected_date(collection.start_date, count)
            collection.save(update_fields=['end_date', 'updated_at'])

def apply_type_change(collection, previous_type):
    """
    Keep stored days when a trip becomes a folder.

    A folder that becomes a trip shows those days when they exist. With no day
    rows, each linked location that does not already have a placement goes to
    Ideas. Day 1 is not created. Running this again does not add a second Ideas
    row for the same location.
    """
    if previous_type == collection.type:
        return
    if previous_type == 'folder' and collection.type == 'trip' and not is_day_based(collection):
        _seed_unplaced_locations(collection)

def _seed_unplaced_locations(collection):
    from django.contrib.contenttypes.models import ContentType

    from adventures.models import CollectionItineraryItem, Location

    location_ct = ContentType.objects.get_for_model(Location)
    placed = set(
        CollectionItineraryItem.objects.filter(
            collection=collection, content_type=location_ct
        ).values_list('object_id', flat=True)
    )
    order = next_order(collection)
    rows = []
    for location in collection.locations.all():
        if location.pk in placed:
            continue
        rows.append(
            CollectionItineraryItem(
                collection=collection,
                content_type=location_ct,
                object_id=location.pk,
                day=None,
                is_global=False,
                date=None,
                order=order,
            )
        )
        order += 1
    if rows:
        CollectionItineraryItem.objects.bulk_create(rows)

def build_days(collection, count):
    """
    Create days 1..count for a trip that has none yet, placing its linked
    records by date. Without an anchor every record goes to Ideas.
    """
    reg = Registry()
    if not isinstance(count, int) or count < 1:
        raise DayPlanError('Day count must be at least 1.')
    if is_day_based(collection, reg):
        raise DayPlanError('This trip is already planned by days.', code='conflict')
    with transaction.atomic():
        _build_day_plan(collection, count, reg)
        sync_projection(collection)

def _build_day_plan(collection, count, reg):
    anchor = collection.start_date

    legacy_days = {
        day.date: day
        for day in reg.Day.objects.filter(collection_id=collection.pk, index__isnull=True)
    }
    days_by_index = {}
    pending = []
    now = datetime.datetime.now(datetime.timezone.utc)
    for index in range(1, count + 1):
        day_date = projected_date(anchor, index)
        day = legacy_days.pop(day_date, None) if day_date else None
        if day is not None:
            day.index = index
            day.save(update_fields=['index'])
            days_by_index[index] = day
        else:
            pending.append(
                reg.Day(
                    collection_id=collection.pk,
                    index=index,
                    date=day_date,
                    created_at=now,
                    updated_at=now,
                )
            )
    if pending:
        for day in reg.Day.objects.bulk_create(pending, batch_size=500):
            days_by_index[day.index] = day
    for leftover in legacy_days.values():
        leftover.delete()

    last_date = projected_date(anchor, count)

    def to_index(value):
        if anchor is None or value is None:
            return None
        index = (value - anchor).days + 1
        return index if 1 <= index <= count else None

    def clamp_range(start, end):
        """Day indexes covered by [start, end], clipped to the built days."""
        if anchor is None or start is None:
            return None
        end = max(end or start, start)
        if end < anchor or start > last_date:
            return None
        return to_index(max(start, anchor)), to_index(min(end, last_date))

    rows = list(reg.Item.objects.filter(collection_id=collection.pk).order_by('order', 'created_at'))

    # Retarget Visit rows to their location.
    location_ct = reg.ct('location')
    for row in rows:
        if reg.ct_name(row.content_type_id) == 'visit':
            visit = reg.Visit.objects.filter(pk=row.object_id).first()
            if visit is None:
                row.delete()
                row.pk = None
                continue
            row.content_type_id = location_ct.pk
            row.object_id = visit.location_id
    rows = [row for row in rows if row.pk is not None]

    rows_by_object = {}
    for row in rows:
        name = reg.ct_name(row.content_type_id)
        rows_by_object.setdefault((name, str(row.object_id)), []).append(row)

    objects = {}
    for location in reg.Location.objects.filter(collections__id=collection.pk).distinct():
        objects[('location', str(location.pk))] = location
    for name, model in (
        ('lodging', reg.Lodging),
        ('transportation', reg.Transportation),
        ('note', reg.Note),
        ('checklist', reg.Checklist),
    ):
        for obj in model.objects.filter(collection_id=collection.pk):
            objects[(name, str(obj.pk))] = obj

    model_by_name = {
        'location': reg.Location,
        'lodging': reg.Lodging,
        'transportation': reg.Transportation,
        'note': reg.Note,
        'checklist': reg.Checklist,
    }
    for key in rows_by_object:
        name, object_id = key
        if key not in objects and name in model_by_name:
            obj = model_by_name[name].objects.filter(pk=object_id).first()
            if obj is not None:
                objects[key] = obj

    plans = []  # (row or None, name, object_id, target)
    rows_to_delete = []

    for key, rows_for_object in rows_by_object.items():
        if key not in objects:
            rows_to_delete.extend(rows_for_object)

    for key, obj in objects.items():
        name, object_id = key
        object_rows = rows_by_object.get(key, [])
        dated_rows = [r for r in object_rows if not r.is_global and r.date]
        has_global = any(r.is_global for r in object_rows)
        row_indexes = {to_index(r.date) for r in dated_rows} - {None}
        targets = []

        if name == 'location':
            indexes = set(row_indexes)
            if has_global or not object_rows:
                for visit in reg.Visit.objects.filter(location_id=obj.pk):
                    start = local_date(visit.start_date, visit.timezone)
                    end = local_date(visit.end_date, visit.timezone) or start
                    covered = clamp_range(start, end)
                    if covered:
                        indexes.update(range(covered[0], covered[1] + 1))
            for start, end in contiguous_runs(indexes):
                targets.append(_Target('day', start, end if end > start else None))
        elif name == 'lodging':
            covered = None
            if obj.check_in:
                start = local_date(obj.check_in, obj.timezone)
                checkout = local_date(obj.check_out, obj.timezone) if obj.check_out else None
                last_night = checkout - datetime.timedelta(days=1) if checkout else start
                covered = clamp_range(start, max(last_night, start))
            elif row_indexes:
                first_run = contiguous_runs(row_indexes)[0]
                covered = first_run
            if covered:
                targets.append(_Target('day', covered[0], covered[1] if covered[1] > covered[0] else None))
        elif name == 'transportation':
            covered = None
            if obj.date:
                start = local_date(obj.date, obj.start_timezone)
                end = local_date(obj.end_date, obj.end_timezone) if obj.end_date else start
                covered = clamp_range(start, end)
            elif row_indexes:
                covered = (min(row_indexes), min(row_indexes))
            if covered:
                targets.append(_Target('day', covered[0], covered[1] if covered[1] > covered[0] else None))
        else:
            if has_global:
                targets.append(_Target('global'))
            indexes = set(row_indexes)
            if not object_rows:
                index = to_index(obj.date)
                if index:
                    indexes.add(index)
            for index in sorted(indexes):
                targets.append(_Target('day', index, None))

        if not targets:
            targets.append(_Target('ideas'))

        available = list(object_rows)
        for target in targets:
            chosen = None
            if target.bucket == 'global':
                chosen = next((r for r in available if r.is_global), None)
            elif target.bucket == 'day':
                chosen = next(
                    (r for r in available if not r.is_global and to_index(r.date) == target.start),
                    None,
                )
                if chosen is None:
                    chosen = next((r for r in available if not r.is_global), None)
            if chosen is None and available and target.bucket != 'global':
                chosen = available[0]
            if chosen is not None:
                available.remove(chosen)
            kept_place = (
                chosen is not None
                and (
                    (target.bucket == 'global' and chosen.is_global)
                    or (target.bucket == 'day' and not chosen.is_global and to_index(chosen.date) == target.start)
                )
            )
            target.rank = (
                0 if kept_place else 1,
                chosen.order if chosen is not None else 0,
                TYPE_PRIORITY.get(name, 9),
                str(getattr(obj, 'name', '') or ''),
            )
            plans.append((chosen, name, object_id, target))
        rows_to_delete.extend(available)

    for row in rows_to_delete:
        if row.pk:
            reg.Item.objects.filter(pk=row.pk).delete()

    kept_rows = [plan[0] for plan in plans if plan[0] is not None]
    for offset, row in enumerate(kept_rows):
        reg.Item.objects.filter(pk=row.pk).update(order=TEMP_ORDER_OFFSET + offset)

    buckets = {}
    for plan in plans:
        target = plan[3]
        bucket_key = ('day', target.start) if target.bucket == 'day' else (target.bucket,)
        buckets.setdefault(bucket_key, []).append(plan)

    for bucket_key, bucket_plans in buckets.items():
        bucket_plans.sort(key=lambda plan: plan[3].rank)
        for order, (row, name, object_id, target) in enumerate(bucket_plans):
            if target.bucket == 'day':
                day = days_by_index[target.start]
                values = dict(day_id=day.pk, date=day.date, is_global=False, span_end_index=target.end)
            elif target.bucket == 'global':
                values = dict(day_id=None, date=None, is_global=True, span_end_index=None)
            else:
                values = dict(day_id=None, date=None, is_global=False, span_end_index=None)
            if row is not None:
                reg.Item.objects.filter(pk=row.pk).update(
                    content_type_id=row.content_type_id,
                    object_id=row.object_id,
                    order=order,
                    **values,
                )
            else:
                reg.Item.objects.create(
                    collection_id=collection.pk,
                    content_type_id=reg.ct(name).pk,
                    object_id=object_id,
                    order=order,
                    **values,
                )
