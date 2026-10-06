"""
Day-based trip planning.

A converted trip stores contiguous ``CollectionItineraryDay`` rows indexed 1..N.
``Collection.start_date`` is the optional anchor; ``end_date`` is derived as the
last projected day. Placements (``CollectionItineraryItem``) sit on a day, in
Ideas (no day, not global), or trip-wide (global notes and checklists).

``convert_collection`` is the single idempotent conversion used by the data
migration and by backup import. The other helpers back the itinerary actions
and only run against live models.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Iterable

from django.apps import apps as global_apps
from django.db import transaction
from django.db.models import Max, Q

MAX_AUTO_BUILD_DAYS = 21
MAX_PLAN_DAYS = 62
DEFAULT_PLAN_DAYS = 21
TEMP_ORDER_OFFSET = 1_000_000

SPAN_TYPES = ('lodging', 'transportation')
GLOBAL_TYPES = ('note', 'checklist')
PLACEABLE_TYPES = ('location', 'lodging', 'transportation', 'note', 'checklist')
_TYPE_PRIORITY = {'lodging': 0, 'location': 1, 'transportation': 2, 'note': 3, 'checklist': 4}


class DayPlanError(Exception):
    """A request the day plan cannot apply; ``code`` maps to an HTTP status."""

    def __init__(self, message, code='invalid', extra=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.extra = extra or {}


class _Registry:
    def __init__(self, apps=None):
        get_model = (apps or global_apps).get_model
        self.Collection = get_model('adventures', 'Collection')
        self.Day = get_model('adventures', 'CollectionItineraryDay')
        self.Item = get_model('adventures', 'CollectionItineraryItem')
        self.Visit = get_model('adventures', 'Visit')
        self.Location = get_model('adventures', 'Location')
        self.Lodging = get_model('adventures', 'Lodging')
        self.Transportation = get_model('adventures', 'Transportation')
        self.Note = get_model('adventures', 'Note')
        self.Checklist = get_model('adventures', 'Checklist')
        self.ContentType = get_model('contenttypes', 'ContentType')
        self._ct_cache = {}
        self._ct_names = {}

    def ct(self, name):
        if name not in self._ct_cache:
            ct, _ = self.ContentType.objects.get_or_create(app_label='adventures', model=name)
            self._ct_cache[name] = ct
            self._ct_names[ct.pk] = name
        return self._ct_cache[name]

    def ct_name(self, ct_id):
        if ct_id not in self._ct_names:
            ct = self.ContentType.objects.filter(pk=ct_id).first()
            self._ct_names[ct_id] = ct.model if ct else None
        return self._ct_names[ct_id]


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------

def _tzinfo(name):
    from zoneinfo import ZoneInfo

    try:
        return ZoneInfo(name) if name else datetime.timezone.utc
    except Exception:
        return datetime.timezone.utc


def _is_all_day(value):
    utc_value = value.astimezone(datetime.timezone.utc)
    return utc_value.time() in (datetime.time.min, datetime.time.max)


def local_date(value, tz_name=None):
    """Calendar date of a stored datetime. UTC midnight is a date-only value."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        if _is_all_day(value):
            return value.astimezone(datetime.timezone.utc).date()
        return value.astimezone(_tzinfo(tz_name)).date()
    return value


def _all_day(day):
    return datetime.datetime.combine(day, datetime.time.min, tzinfo=datetime.timezone.utc)


def move_to_date(existing, new_day, tz_name=None, fallback_time=None):
    """Put ``new_day`` on a datetime, keeping the clock time it already had."""
    if existing is not None:
        if existing.tzinfo is None:
            existing = existing.replace(tzinfo=datetime.timezone.utc)
        if _is_all_day(existing):
            return _all_day(new_day)
        tz = _tzinfo(tz_name)
        local_time = existing.astimezone(tz).time()
        return datetime.datetime.combine(new_day, local_time, tzinfo=tz).astimezone(datetime.timezone.utc)
    if fallback_time is not None:
        tz = _tzinfo(tz_name)
        return datetime.datetime.combine(new_day, fallback_time, tzinfo=tz).astimezone(datetime.timezone.utc)
    return _all_day(new_day)


def projected_date(anchor, index):
    if anchor is None or index is None:
        return None
    return anchor + datetime.timedelta(days=index - 1)


def inclusive_span(start, end):
    if not start or not end:
        return None
    return (end - start).days + 1


def _runs(indexes: Iterable[int]):
    values = sorted(set(indexes))
    runs = []
    for value in values:
        if runs and value == runs[-1][1] + 1:
            runs[-1][1] = value
        else:
            runs.append([value, value])
    return [(start, end) for start, end in runs]


def _date_range(start, end):
    current = start
    while current <= end:
        yield current
        current += datetime.timedelta(days=1)


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def is_day_based(collection, registry=None) -> bool:
    reg = registry or _Registry()
    return reg.Day.objects.filter(collection_id=collection.pk, index__isnull=False).exists()


def _has_legacy_dated_items(collection) -> bool:
    """Date-keyed rows that have not been converted to a day index."""
    from adventures.models import CollectionItineraryItem

    return CollectionItineraryItem.objects.filter(
        collection=collection, date__isnull=False, day__isnull=True
    ).exists()


def indexed_days(collection, registry=None):
    reg = registry or _Registry()
    return list(reg.Day.objects.filter(collection_id=collection.pk, index__isnull=False).order_by('index'))


def day_count(collection, registry=None):
    reg = registry or _Registry()
    return reg.Day.objects.filter(collection_id=collection.pk, index__isnull=False).count()


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------

@dataclass
class _Target:
    bucket: str  # 'day' | 'ideas' | 'global'
    start: int | None = None
    end: int | None = None
    rank: tuple = field(default_factory=tuple)


def convert_collection(collection, apps=None) -> bool:
    """
    Convert a date-keyed trip of 21 days or fewer to a day plan.

    Idempotent: a collection that already has day indexes, a folder, an undated
    trip, or a trip longer than 21 days is left unchanged. Returns True when
    days were built.
    """
    reg = _Registry(apps)
    if collection.type != 'trip':
        return False
    if is_day_based(collection, reg):
        return False
    span = inclusive_span(collection.start_date, collection.end_date)
    if span is None or span < 1 or span > MAX_AUTO_BUILD_DAYS:
        return False
    _build_day_plan(collection, span, reg)
    return True


def plan_by_days(collection, count=DEFAULT_PLAN_DAYS):
    """Build ``count`` days from the anchor for a long date-keyed trip."""
    reg = _Registry()
    if collection.type != 'trip':
        raise DayPlanError('Only trips can be planned by days.')
    if is_day_based(collection, reg):
        raise DayPlanError('This trip is already planned by days.', code='conflict')
    if not isinstance(count, int) or count < 1:
        raise DayPlanError('Day count must be at least 1.')
    if count > MAX_PLAN_DAYS:
        raise DayPlanError(
            f'A trip can have at most {MAX_PLAN_DAYS} days. Split this collection into shorter trips.',
            code='too_many_days',
        )
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
    order = _next_order(collection)
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
    reg = _Registry()
    if count < 1 or count > MAX_PLAN_DAYS:
        raise DayPlanError(f'Day count must be between 1 and {MAX_PLAN_DAYS}.')
    if is_day_based(collection, reg):
        raise DayPlanError('This trip is already planned by days.', code='conflict')
    _build_day_plan(collection, count, reg)
    sync_projection(collection)


def _build_day_plan(collection, count, reg):
    anchor = collection.start_date

    legacy_days = {
        day.date: day
        for day in reg.Day.objects.filter(collection_id=collection.pk, index__isnull=True)
    }
    days_by_index = {}
    for index in range(1, count + 1):
        day_date = projected_date(anchor, index)
        day = legacy_days.pop(day_date, None) if day_date else None
        if day is not None:
            day.index = index
            day.save(update_fields=['index'])
        else:
            day = reg.Day.objects.create(collection_id=collection.pk, index=index, date=day_date)
        days_by_index[index] = day
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
            for start, end in _runs(indexes):
                targets.append(_Target('day', start, end if end > start else None))
        elif name == 'lodging':
            covered = None
            if obj.check_in:
                start = local_date(obj.check_in, obj.timezone)
                checkout = local_date(obj.check_out, obj.timezone) if obj.check_out else None
                last_night = checkout - datetime.timedelta(days=1) if checkout else start
                covered = clamp_range(start, max(last_night, start))
            elif row_indexes:
                first_run = _runs(row_indexes)[0]
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
                _TYPE_PRIORITY.get(name, 9),
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


# ---------------------------------------------------------------------------
# Projection and object date writes (live models)
# ---------------------------------------------------------------------------

def _item_type(item):
    return item.content_type.model


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
    item_type = _item_type(item)
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

    departure = move_to_date(obj.date, start_day, obj.start_timezone, item.start_time)
    arrival = obj.end_date
    if obj.end_date is not None or end_index != start_index or item.end_time is not None:
        arrival = move_to_date(obj.end_date, end_day, obj.end_timezone or obj.start_timezone, item.end_time)
        if arrival < departure:
            arrival = departure
    if obj.date == departure and obj.end_date == arrival:
        return obj
    obj.date, obj.end_date = departure, arrival
    obj.save(update_fields=['date', 'end_date', 'updated_at'])
    return obj


def clear_object_dates(item):
    item_type = _item_type(item)
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


def _span_snapshot(collection):
    from adventures.models import CollectionItineraryItem

    snapshot = {}
    for item in CollectionItineraryItem.objects.filter(collection=collection, day__isnull=False).select_related('day', 'content_type'):
        if _item_type(item) in SPAN_TYPES:
            snapshot[item.pk] = span_bounds(item)
    return snapshot


def _rewrite_changed_spans(collection, before, force=False):
    """Rewrite lodging and transport dates whose projected days changed."""
    from adventures.models import CollectionItineraryItem

    if collection.start_date is None:
        return []
    updated = []
    items = CollectionItineraryItem.objects.filter(collection=collection, day__isnull=False).select_related('day', 'content_type')
    for item in items:
        if _item_type(item) not in SPAN_TYPES:
            continue
        if force or before.get(item.pk) != span_bounds(item):
            obj = write_object_dates(item, collection.start_date)
            if obj is not None:
                updated.append(obj)
    return updated


# ---------------------------------------------------------------------------
# Day operations
# ---------------------------------------------------------------------------

def _lock(collection):
    from adventures.models import Collection

    return Collection.objects.select_for_update().get(pk=collection.pk)


def _require_day_based(collection):
    if not is_day_based(collection):
        raise DayPlanError('This trip is not planned by days yet.', code='not_day_based')


def _renumber(days):
    """Two-phase index write so the partial unique index never collides."""
    from adventures.models import CollectionItineraryDay

    for offset, day in enumerate(days):
        day.index = TEMP_ORDER_OFFSET + offset
    CollectionItineraryDay.objects.bulk_update(days, ['index'])
    for position, day in enumerate(days, start=1):
        day.index = position
    CollectionItineraryDay.objects.bulk_update(days, ['index'])


def _next_order(collection, *, day=None, is_global=False):
    from adventures.models import CollectionItineraryItem

    qs = CollectionItineraryItem.objects.filter(collection=collection)
    if day is not None:
        qs = qs.filter(day=day)
    elif is_global:
        qs = qs.filter(is_global=True)
    else:
        qs = qs.filter(day__isnull=True, is_global=False, date__isnull=True)
    current = qs.aggregate(max_order=Max('order'))['max_order']
    return 0 if current is None else current + 1


def _spanning_items(collection):
    from adventures.models import CollectionItineraryItem

    return list(
        CollectionItineraryItem.objects.filter(
            collection=collection, day__isnull=False, span_end_index__isnull=False
        ).select_related('day', 'content_type')
    )


def _save_spans(items):
    from adventures.models import CollectionItineraryItem

    for item in items:
        if item.span_end_index is not None and item.day_id and item.span_end_index <= item.day.index:
            item.span_end_index = None
    if items:
        CollectionItineraryItem.objects.bulk_update(items, ['day', 'span_end_index'])


def insert_day(collection, position=None, name=None, description=None):
    """Insert an empty day before ``position`` (1-based); default appends."""
    from adventures.models import CollectionItineraryDay

    with transaction.atomic():
        collection = _lock(collection)
        if not is_day_based(collection):
            if collection.type != 'trip' or _has_legacy_dated_items(collection):
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
        if len(days) >= MAX_PLAN_DAYS:
            raise DayPlanError(f'A trip can have at most {MAX_PLAN_DAYS} days.', code='too_many_days')
        count = len(days)
        position = count + 1 if position is None else int(position)
        if position < 1 or position > count + 1:
            raise DayPlanError('Position is outside the trip.')
        before = _span_snapshot(collection)

        spans = _spanning_items(collection)
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
        _renumber(days)
        for item in spans:
            item.day = next(d for d in days if d.pk == item.day_id)
        _save_spans(spans)
        sync_projection(collection, days)
        _rewrite_changed_spans(collection, before)
        return new_day


def duplicate_day(collection, day_id):
    """Insert a copy of a day after it, with its location, note, and checklist stops."""
    from adventures.models import CollectionItineraryItem

    with transaction.atomic():
        collection = _lock(collection)
        _require_day_based(collection)
        source = _get_day(collection, day_id)
        new_day = insert_day(collection, source.index + 1, source.name, source.description)
        source_items = CollectionItineraryItem.objects.filter(collection=collection, day=source).select_related('content_type').order_by('order')
        order = 0
        for item in source_items:
            if _item_type(item) in SPAN_TYPES:
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
        collection = _lock(collection)
        _require_day_based(collection)
        days = indexed_days(collection)
        day = _get_day(collection, day_id)
        position = int(position)
        if position < 1 or position > len(days):
            raise DayPlanError('Position is outside the trip.')
        before = _span_snapshot(collection)
        spans = _spanning_items(collection)
        lengths = {item.pk: item.span_end_index - item.day.index for item in spans}

        days = [d for d in days if d.pk != day.pk]
        days.insert(position - 1, day)
        _renumber(days)
        by_pk = {d.pk: d for d in days}
        for item in spans:
            item.day = by_pk[item.day_id]
            item.span_end_index = min(item.day.index + lengths[item.pk], len(days))
        _save_spans(spans)
        sync_projection(collection, days)
        _rewrite_changed_spans(collection, before)
        return by_pk[day.pk]


def _day_blocking_items(collection, day):
    """Items that start on ``day`` and do not continue onto a later day."""
    from adventures.models import CollectionItineraryItem

    return [
        item
        for item in CollectionItineraryItem.objects.filter(collection=collection, day=day).select_related('day', 'content_type')
        if not (item.span_end_index and item.span_end_index > day.index)
    ]


def delete_day(collection, day_id, destination=None, target_day_id=None):
    """
    Delete a day. Indexes stay contiguous and spans shrink around it.

    A day with stops needs ``destination``: ``ideas``, or ``day`` with
    ``target_day_id``. A span that starts on this day moves to the next day.
    """
    from adventures.models import CollectionItineraryItem

    with transaction.atomic():
        collection = _lock(collection)
        _require_day_based(collection)
        days = indexed_days(collection)
        day = _get_day(collection, day_id)
        if len(days) <= 1:
            raise DayPlanError('A trip needs at least one day.')
        blocking = _day_blocking_items(collection, day)
        target_day = None
        if blocking:
            if destination not in ('day', 'ideas'):
                raise DayPlanError(
                    'This day has stops. Choose where they go.',
                    code='destination_required',
                    extra={'item_count': len(blocking)},
                )
            if destination == 'day':
                target_day = _get_day(collection, target_day_id)
                if target_day.pk == day.pk:
                    raise DayPlanError('Choose a different day for these stops.')

        before = _span_snapshot(collection)
        removed = day.index
        remaining = [d for d in days if d.pk != day.pk]
        next_day = next((d for d in remaining if d.index == removed + 1), None)

        def new_index(old):
            return old if old < removed else old - 1

        spans = _spanning_items(collection)
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
            _place_after_existing(collection, next_day, moved_starts)

        ideas_moves = []
        if blocking:
            for item in blocking:
                item.span_end_index = None
            CollectionItineraryItem.objects.bulk_update(blocking, ['span_end_index'])
            if destination == 'day':
                _place_after_existing(collection, target_day, blocking)
            else:
                order = _next_order(collection)
                for offset, item in enumerate(blocking):
                    item.order = TEMP_ORDER_OFFSET + offset
                CollectionItineraryItem.objects.bulk_update(blocking, ['order'])
                for offset, item in enumerate(blocking):
                    item.day = None
                    item.date = None
                    item.order = order + offset
                    ideas_moves.append(item)
                CollectionItineraryItem.objects.bulk_update(blocking, ['day', 'date', 'order'])

        day.delete()
        _renumber(remaining)
        sync_projection(collection, remaining)
        for item in ideas_moves:
            clear_object_dates(item)
        _rewrite_changed_spans(collection, before)


def _place_after_existing(collection, day, items):
    """Give ``items`` the next free orders on ``day`` (two-phase)."""
    from adventures.models import CollectionItineraryItem

    for offset, item in enumerate(items):
        item.order = TEMP_ORDER_OFFSET + 500_000 + offset
    CollectionItineraryItem.objects.bulk_update(items, ['order'])
    ids = [item.pk for item in items]
    current = (
        CollectionItineraryItem.objects.filter(collection=collection, day=day)
        .exclude(pk__in=ids)
        .aggregate(max_order=Max('order'))['max_order']
    )
    start = 0 if current is None else current + 1
    for offset, item in enumerate(items):
        item.day = day
        item.date = day.date
        item.order = start + offset
    CollectionItineraryItem.objects.bulk_update(items, ['day', 'date', 'order'])


def set_duration(collection, count, anchor=..., destination=None, target_day_id=None, timezone_name=None):
    """
    Set the day count and, optionally, the anchor.

    Adding days appends empty days. Shortening removes trailing days; a trailing
    day with stops needs ``destination`` the same way delete does. ``anchor`` is
    a date or None; omit it to keep the current anchor.
    """
    with transaction.atomic():
        collection = _lock(collection)
        if not is_day_based(collection):
            if collection.type != 'trip' or _has_legacy_dated_items(collection):
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
        if count > MAX_PLAN_DAYS:
            raise DayPlanError(
                f'A trip can have at most {MAX_PLAN_DAYS} days. Split this collection into shorter trips.',
                code='too_many_days',
            )

        days = indexed_days(collection)
        current = len(days)
        if count < current:
            trailing = days[count:]
            blocked = [d for d in trailing if _day_blocking_items(collection, d)]
            if blocked and destination not in ('day', 'ideas'):
                raise DayPlanError(
                    'The days being removed have stops. Choose where they go.',
                    code='destination_required',
                    extra={'day_indexes': [d.index for d in blocked]},
                )
            if destination == 'day':
                target = _get_day(collection, target_day_id)
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
        collection = _lock(collection)
        _require_day_based(collection)
        fields = []
        if collection.start_date != anchor:
            collection.start_date = anchor
            fields.append('start_date')
        if timezone_name:
            from adventures.utils.timezones import validate_timezone
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
            _rewrite_changed_spans(collection, {}, force=True)
        return collection


def _get_day(collection, day_id):
    from adventures.models import CollectionItineraryDay

    if day_id is None:
        raise DayPlanError('A day is required.')
    try:
        return CollectionItineraryDay.objects.get(collection=collection, pk=day_id, index__isnull=False)
    except (CollectionItineraryDay.DoesNotExist, ValueError, TypeError):
        from django.core.exceptions import ValidationError as DjangoValidationError

        raise DayPlanError('Day not found.', code='not_found')
    except DjangoValidationError:
        raise DayPlanError('Day not found.', code='not_found')


def get_day_by_index(collection, index):
    from adventures.models import CollectionItineraryDay

    try:
        return CollectionItineraryDay.objects.get(collection=collection, index=int(index))
    except (CollectionItineraryDay.DoesNotExist, ValueError, TypeError):
        raise DayPlanError('Day not found.', code='not_found')


# ---------------------------------------------------------------------------
# Placements
# ---------------------------------------------------------------------------

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
        collection = _lock(collection)
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

        target_order = _next_order(collection, day=day, is_global=is_global)
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
            _reorder_bucket(collection, item, int(order))
        if day is not None:
            write_object_dates(item, collection.start_date)
        elif not is_global:
            clear_object_dates(item)
        return item, True


def _bucket_queryset(collection, *, day=None, is_global=False):
    from adventures.models import CollectionItineraryItem

    qs = CollectionItineraryItem.objects.filter(collection=collection)
    if day is not None:
        return qs.filter(day=day)
    if is_global:
        return qs.filter(is_global=True)
    return qs.filter(day__isnull=True, is_global=False, date__isnull=True)


def _reorder_bucket(collection, item, position):
    """Move ``item`` to ``position`` inside its bucket and close the gaps."""
    from adventures.models import CollectionItineraryItem

    members = list(
        _bucket_queryset(collection, day=item.day if item.day_id else None, is_global=item.is_global)
        .exclude(pk=item.pk)
        .order_by('order', 'created_at')
    )
    position = max(0, min(position, len(members)))
    members.insert(position, item)
    for offset, member in enumerate(members):
        member.order = TEMP_ORDER_OFFSET + offset
    CollectionItineraryItem.objects.bulk_update(members, ['order'])
    for offset, member in enumerate(members):
        member.order = offset
    CollectionItineraryItem.objects.bulk_update(members, ['order'])


def move_placement(collection, item, *, day=None, is_global=False, order=None, span_end_index=None, span_given=False):
    """Move one placement and write or clear lodging and transport dates with it."""
    from adventures.models import CollectionItineraryItem

    item_type = _item_type(item)
    if is_global and item_type not in GLOBAL_TYPES:
        raise DayPlanError('Only notes and checklists can be trip-wide.')

    with transaction.atomic():
        collection = _lock(collection)
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
        item.order = _next_order(collection, day=day, is_global=item.is_global)
        item.save(update_fields=['day', 'date', 'is_global', 'span_end_index', 'order', 'updated_at'])

        if order is not None:
            _reorder_bucket(collection, item, int(order))
        _compact_bucket(collection, *old_bucket)

        if day is not None:
            write_object_dates(item, collection.start_date)
        elif not is_global:
            clear_object_dates(item)
        return item


def _compact_bucket(collection, day_id, is_global):
    from adventures.models import CollectionItineraryDay, CollectionItineraryItem

    day = CollectionItineraryDay.objects.filter(pk=day_id).first() if day_id else None
    members = list(_bucket_queryset(collection, day=day, is_global=is_global).order_by('order', 'created_at'))
    if [m.order for m in members] == list(range(len(members))):
        return
    for offset, member in enumerate(members):
        member.order = TEMP_ORDER_OFFSET * 4 + offset
    CollectionItineraryItem.objects.bulk_update(members, ['order'])
    for offset, member in enumerate(members):
        member.order = offset
    CollectionItineraryItem.objects.bulk_update(members, ['order'])


def reorder_day_plan(collection, entries):
    """
    Apply a batch of placements in one transaction.

    Each entry is ``{"id", "day_index" | None, "is_global", "order", "span_end_index"?}``.
    Lodging and transport dates move in the same transaction.
    """
    from adventures.models import CollectionItineraryItem

    with transaction.atomic():
        collection = _lock(collection)
        _require_day_based(collection)
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
            item_type = _item_type(item)
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
            _compact_bucket(collection, day_id, is_global)
        return [items[str(entry['id'])] for entry in entries], updated_objects


# ---------------------------------------------------------------------------
# Visits
# ---------------------------------------------------------------------------

def _visit_on_dates(location_id, start, end):
    """An existing visit whose dates overlap this stop. The earliest start wins."""
    from adventures.models import Visit

    match = None
    match_start = None
    for visit in Visit.objects.filter(location_id=location_id):
        visit_start = local_date(visit.start_date, visit.timezone)
        visit_end = local_date(visit.end_date, visit.timezone) or visit_start
        if visit_start is None or visit_end is None:
            continue
        if visit_start <= end and visit_end >= start and (match_start is None or visit_start < match_start):
            match = visit
            match_start = visit_start
    return match


def log_visited(item, visit_date=None):
    """
    Create one visit for a location placement, or return one that already covers it.

    A visit logged earlier on these dates is linked instead of copied. Uses the
    projected date; ``visit_date`` is required when the trip has no anchor or the
    placement is in Ideas. Both visit bounds are always set.
    """
    from adventures.models import Visit

    if _item_type(item) != 'location':
        raise DayPlanError('Only location stops can be logged as visited.')
    if item.logged_visit_id:
        return item.logged_visit, False

    with transaction.atomic():
        anchor = item.collection.start_date
        start_index, end_index = span_bounds(item)
        start_day = projected_date(anchor, start_index) if start_index else None
        end_day = projected_date(anchor, end_index) if end_index else None
        if visit_date is not None:
            span_days = (end_index - start_index) if start_index else 0
            start_day = visit_date
            end_day = visit_date + datetime.timedelta(days=span_days)
        if start_day is None:
            raise DayPlanError('Choose the date you visited.', code='date_required')

        existing = _visit_on_dates(item.object_id, start_day, end_day or start_day)
        if existing is not None:
            item.logged_visit = existing
            item.save(update_fields=['logged_visit', 'updated_at'])
            return existing, False

        visit = Visit.objects.create(
            location_id=item.object_id,
            start_date=_all_day(start_day),
            end_date=_all_day(end_day or start_day),
            timezone=item.timezone or None,
        )
        item.logged_visit = visit
        item.save(update_fields=['logged_visit', 'updated_at'])
        return visit, True


def log_day(collection, day, visit_date=None):
    """Log every non-optional location stop on ``day`` that has no logged visit."""
    from adventures.models import CollectionItineraryItem

    items = CollectionItineraryItem.objects.filter(
        collection=collection,
        day=day,
        is_optional=False,
        logged_visit__isnull=True,
        content_type__model='location',
    ).select_related('day', 'content_type', 'collection').order_by('order')
    if not items:
        return []
    if collection.start_date is None and visit_date is None:
        raise DayPlanError('Choose the date you visited.', code='date_required')
    logged = []
    with transaction.atomic():
        for item in items:
            visit, _ = log_visited(item, visit_date)
            logged.append(item)
    return logged
