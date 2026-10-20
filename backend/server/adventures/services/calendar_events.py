from __future__ import annotations

from datetime import date, datetime, timedelta, timezone as dt_timezone
from typing import Iterable

from django.db.models import Prefetch, Q, prefetch_related_objects
from django.utils import timezone

from adventures.models import (
    Activity,
    Checklist,
    Collection,
    CollectionItineraryItem,
    Location,
    Lodging,
    Note,
    Transportation,
    Visit,
)
from core.dates import is_midnight_utc
from core.parsing import parse_iso_date
from adventures.services.day_plan import local_date, projected_date, span_bounds

CALENDAR_EVENT_COLORS = {
    'visit': '#3b82f6',
    'transportation': '#f97316',
    'lodging': '#8b5cf6',
    'collection': '#10b981',
    'note': '#6366f1',
    'checklist': '#14b8a6',
    'stop': '#0ea5e9',
    'activity': '#ef4444',
}

ALL_EVENT_TYPES = tuple(CALENDAR_EVENT_COLORS.keys())

TRANSPORT_ICONS = {
    'flight': '✈️',
    'train': '🚆',
    'bus': '🚌',
    'car': '🚗',
    'boat': '🚢',
}


def _parse_types_param(value: str | None) -> set[str]:
    if not value:
        return set(ALL_EVENT_TYPES)
    requested = {item.strip().lower() for item in value.split(',') if item.strip()}
    return requested & set(ALL_EVENT_TYPES) or set(ALL_EVENT_TYPES)


def _member_collections(user):
    return Collection.objects.filter(Q(user=user.id) | Q(shared_with=user.id)).distinct()


def _calendar_collections(user):
    """
    Collections whose events reach this user's calendar.

    Archived collections are left out, and so are trips with no anchor: their
    days have no calendar date yet. That holds for the owner too.
    """
    return (
        _member_collections(user)
        .exclude(is_archived=True)
        .exclude(type=Collection.Type.TRIP, start_date__isnull=True)
    )


def _is_day_plan_q():
    """A trip planned by days. A folder keeps saved days hidden, so it is not one."""
    return Q(type=Collection.Type.TRIP, itinerary_days__index__isnull=False)


def _child_queryset(model, user):
    """
    Lodging, transport, notes, and checklists the user sees outside a day plan.

    Children of a day-based trip are emitted from their placements instead, and
    children of hidden collections are dropped.
    """
    visible = _calendar_collections(user).exclude(_is_day_plan_q()).values('id')
    return (
        model.objects.filter(
            Q(user=user.id, collection__isnull=True) | Q(collection__in=visible)
        )
        .select_related('collection')
        .distinct()
    )


def _to_iso(value: datetime | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            value = timezone.make_aware(value, dt_timezone.utc)
        return value.isoformat().replace('+00:00', 'Z')
    return value.isoformat()


def _event_overlaps_range(
    start: datetime | date | None,
    end: datetime | date | None,
    range_start: date | None,
    range_end: date | None,
) -> bool:
    if start is None:
        return False
    if range_start is None and range_end is None:
        return True

    if isinstance(start, datetime):
        event_start = start.date()
    else:
        event_start = start

    if end is None:
        event_end = event_start
    elif isinstance(end, datetime):
        event_end = end.date()
    else:
        event_end = end

    if range_start and event_end < range_start:
        return False
    if range_end and event_start > range_end:
        return False
    return True


def _build_event(
    *,
    event_id: str,
    event_type: str,
    title: str,
    start: datetime | date,
    end: datetime | date | None,
    all_day: bool,
    timezone_name: str | None,
    icon: str,
    category: str,
    location_label: str = '',
    description: str = '',
    url: str = '',
    resource_id: str = '',
    collection_id: str | None = None,
    collection_name: str | None = None,
) -> dict:
    return {
        'id': event_id,
        'type': event_type,
        'title': title,
        'start': _to_iso(start),
        'end': _to_iso(end or start),
        'all_day': all_day,
        'timezone': timezone_name,
        'color': CALENDAR_EVENT_COLORS.get(event_type, '#64748b'),
        'icon': icon,
        'category': category,
        'location_label': location_label or '',
        'description': description or '',
        'url': url or '',
        'resource_id': resource_id or '',
        'collection_id': collection_id,
        'collection_name': collection_name,
    }


def _visit_events(
    user,
    range_start: date | None,
    range_end: date | None,
) -> list[dict]:
    events: list[dict] = []
    # A visit stays on the place: only the place's owner sees it, on its own dates.
    locations = (
        Location.objects.filter(user=user.id)
        .filter(visits__isnull=False)
        .select_related('category')
        .prefetch_related(
            Prefetch(
                'visits',
                queryset=Visit.objects.only(
                    'id', 'location_id', 'start_date', 'end_date', 'timezone', 'notes'
                ),
            ),
            'collections',
        )
        .distinct()
    )

    for location in locations:
        # .first() would bypass the prefetch and query once per place; pick by pk in memory.
        collection = min(location.collections.all(), key=lambda c: c.pk, default=None)
        collection_id = str(collection.id) if collection else None
        collection_name = collection.name if collection else None
        category_name = location.category.name if location.category else 'Adventure'
        category_icon = location.category.icon if location.category else '📍'

        for visit in location.visits.all():
            if not visit.start_date:
                continue
            if not _event_overlaps_range(
                visit.start_date, visit.end_date or visit.start_date, range_start, range_end
            ):
                continue

            all_day = is_midnight_utc(visit.start_date)
            events.append(
                _build_event(
                    event_id=f'visit-{visit.id}',
                    event_type='visit',
                    title=location.name,
                    start=visit.start_date,
                    end=visit.end_date or visit.start_date,
                    all_day=all_day,
                    timezone_name=visit.timezone,
                    icon=category_icon,
                    category=category_name,
                    location_label=location.location or '',
                    description=visit.notes or location.description or '',
                    url=f'/locations/{location.id}',
                    resource_id=str(location.id),
                    collection_id=collection_id,
                    collection_name=collection_name,
                )
            )
    return events


def _transportation_events(user, range_start: date | None, range_end: date | None) -> list[dict]:
    events: list[dict] = []
    transportations = _child_queryset(Transportation, user)

    for item in transportations:
        if not item.date:
            continue
        if not _event_overlaps_range(item.date, item.end_date or item.date, range_start, range_end):
            continue

        route = ' → '.join(filter(None, [item.from_location, item.to_location]))
        icon = TRANSPORT_ICONS.get((item.type or '').lower(), '🛣️')
        collection_id = str(item.collection_id) if item.collection_id else None

        events.append(
            _build_event(
                event_id=f'transportation-{item.id}',
                event_type='transportation',
                title=item.name or item.type or 'Transportation',
                start=item.date,
                end=item.end_date or item.date,
                all_day=is_midnight_utc(item.date),
                timezone_name=item.start_timezone or item.end_timezone,
                icon=icon,
                category=item.type or 'Transportation',
                location_label=route,
                description=item.description or '',
                url=f'/transportations/{item.id}',
                resource_id=str(item.id),
                collection_id=collection_id,
                collection_name=item.collection.name if item.collection else None,
            )
        )
    return events


def _lodging_calendar_end(check_in: datetime | None, check_out: datetime | None) -> datetime | date | None:
    if not check_out:
        return check_in
    if not check_in:
        return check_out

    check_in_date = check_in.date() if isinstance(check_in, datetime) else check_in
    check_out_date = check_out.date() if isinstance(check_out, datetime) else check_out
    if check_out_date <= check_in_date:
        return check_out
    return check_out_date - timedelta(days=1)


def _lodging_events(user, range_start: date | None, range_end: date | None) -> list[dict]:
    events: list[dict] = []
    stays = _child_queryset(Lodging, user)

    for stay in stays:
        start = stay.check_in or stay.check_out
        if not start:
            continue
        end = _lodging_calendar_end(stay.check_in, stay.check_out) or start
        if not _event_overlaps_range(start, end, range_start, range_end):
            continue

        collection_id = str(stay.collection_id) if stay.collection_id else None
        events.append(
            _build_event(
                event_id=f'lodging-{stay.id}',
                event_type='lodging',
                title=stay.name,
                start=start,
                end=end,
                all_day=True,
                timezone_name=stay.timezone,
                icon='🏨',
                category=stay.type or 'Lodging',
                location_label=stay.location or '',
                description=stay.description or '',
                url=f'/lodging/{stay.id}',
                resource_id=str(stay.id),
                collection_id=collection_id,
                collection_name=stay.collection.name if stay.collection else None,
            )
        )
    return events


def _collection_events(user, range_start: date | None, range_end: date | None) -> list[dict]:
    events: list[dict] = []
    collections = _calendar_collections(user)

    for collection in collections:
        if not collection.start_date:
            continue
        end = collection.end_date or collection.start_date
        if not _event_overlaps_range(collection.start_date, end, range_start, range_end):
            continue

        events.append(
            _build_event(
                event_id=f'collection-{collection.id}',
                event_type='collection',
                title=collection.name,
                start=collection.start_date,
                end=end,
                all_day=True,
                timezone_name=None,
                icon='🗺️',
                category='Trip',
                location_label='',
                description=collection.description or '',
                url=f'/collections/{collection.id}',
                resource_id=str(collection.id),
                collection_id=str(collection.id),
                collection_name=collection.name,
            )
        )
    return events


def _note_events(user, range_start: date | None, range_end: date | None) -> list[dict]:
    events: list[dict] = []
    notes = _child_queryset(Note, user).filter(date__isnull=False)

    for note in notes:
        if not _event_overlaps_range(note.date, note.date, range_start, range_end):
            continue

        collection_id = str(note.collection_id) if note.collection_id else None
        url = f'/collections/{collection_id}?view=notes' if collection_id else ''
        events.append(
            _build_event(
                event_id=f'note-{note.id}',
                event_type='note',
                title=note.name,
                start=note.date,
                end=note.date,
                all_day=True,
                timezone_name=None,
                icon='📝',
                category='Note',
                description=note.content or '',
                url=url,
                resource_id=str(note.id),
                collection_id=collection_id,
                collection_name=note.collection.name if note.collection else None,
            )
        )
    return events


def _checklist_events(user, range_start: date | None, range_end: date | None) -> list[dict]:
    events: list[dict] = []
    checklists = _child_queryset(Checklist, user).filter(date__isnull=False)

    for checklist in checklists:
        if not _event_overlaps_range(checklist.date, checklist.date, range_start, range_end):
            continue

        collection_id = str(checklist.collection_id) if checklist.collection_id else None
        url = f'/collections/{collection_id}?view=checklists' if collection_id else ''
        events.append(
            _build_event(
                event_id=f'checklist-{checklist.id}',
                event_type='checklist',
                title=checklist.name,
                start=checklist.date,
                end=checklist.date,
                all_day=True,
                timezone_name=None,
                icon='✅',
                category='Checklist',
                url=url,
                resource_id=str(checklist.id),
                collection_id=collection_id,
                collection_name=checklist.collection.name if checklist.collection else None,
            )
        )
    return events


def _plan_clock(day, clock, tz_name):
    """A placement's local time on a projected day, as an aware datetime."""
    from zoneinfo import ZoneInfo

    try:
        tz = ZoneInfo(tz_name) if tz_name else dt_timezone.utc
    except Exception:
        tz = dt_timezone.utc
    return datetime.combine(day, clock, tzinfo=tz)


def _owner_visit_days(user, location_ids) -> set[tuple[str, date]]:
    """(location, date) pairs already on this user's calendar through a visit."""
    covered = set()
    visits = Visit.objects.filter(
        location__user=user.id, location_id__in=location_ids, start_date__isnull=False
    ).select_related('location')
    for visit in visits:
        start = local_date(visit.start_date, visit.timezone)
        end = local_date(visit.end_date, visit.timezone) or start
        current = start
        while current <= end:
            covered.add((str(visit.location_id), current))
            current += timedelta(days=1)
    return covered


def _plan_events(user, range_start: date | None, range_end: date | None) -> list[dict]:
    """
    One event per non-optional placement on an anchored, unarchived day plan.

    Owner and collaborators get the same plan. Ideas, trip-wide items, and
    optional placements have no date and are left out. A span is one event.
    """
    events: list[dict] = []
    collections = (
        _calendar_collections(user)
        .filter(_is_day_plan_q(), start_date__isnull=False)
        .distinct()
    )
    collections = list(collections)
    if not collections:
        return events
    by_id = {c.id: c for c in collections}

    items = list(
        CollectionItineraryItem.objects.filter(
            collection_id__in=by_id.keys(),
            day__isnull=False,
            day__index__isnull=False,
            is_global=False,
            is_optional=False,
        )
        .select_related('day', 'content_type')
        .prefetch_related('item')
        .order_by('day__index', 'order')
    )
    # Each stop reads its place's category: load them for every place at once.
    prefetch_related_objects(
        [i.item for i in items if i.content_type.model == 'location' and i.item is not None],
        'category',
    )
    location_ids = [i.object_id for i in items if i.content_type.model == 'location']
    visit_days = _owner_visit_days(user, location_ids) if location_ids else set()

    for item in items:
        collection = by_id[item.collection_id]
        model = item.content_type.model
        obj = item.item
        if obj is None:
            continue
        start_index, end_index = span_bounds(item)
        first_day = projected_date(collection.start_date, start_index)
        last_day = projected_date(collection.start_date, end_index)
        tz_name = item.timezone or collection.timezone
        common = {
            'collection_id': str(collection.id),
            'collection_name': collection.name,
        }

        if model == 'lodging':
            start = obj.check_in or obj.check_out or first_day
            end = _lodging_calendar_end(obj.check_in, obj.check_out) or last_day
            if not _event_overlaps_range(start, end, range_start, range_end):
                continue
            events.append(_build_event(
                event_id=f'lodging-{obj.id}', event_type='lodging', title=obj.name,
                start=start, end=end, all_day=True, timezone_name=obj.timezone, icon='🏨',
                category=obj.type or 'Lodging', location_label=obj.location or '',
                description=obj.description or '', url=f'/lodging/{obj.id}',
                resource_id=str(obj.id), **common,
            ))
            continue

        if model == 'transportation':
            start = obj.date or first_day
            end = obj.end_date or (obj.date if obj.date else last_day)
            if not _event_overlaps_range(start, end, range_start, range_end):
                continue
            all_day = not isinstance(start, datetime) or is_midnight_utc(start)
            route = ' → '.join(filter(None, [obj.from_location, obj.to_location]))
            events.append(_build_event(
                event_id=f'transportation-{obj.id}', event_type='transportation',
                title=obj.name or obj.type or 'Transportation', start=start, end=end,
                all_day=all_day, timezone_name=obj.start_timezone or obj.end_timezone,
                icon=TRANSPORT_ICONS.get((obj.type or '').lower(), '🛣️'),
                category=obj.type or 'Transportation', location_label=route,
                description=obj.description or '', url=f'/transportations/{obj.id}',
                resource_id=str(obj.id), **common,
            ))
            continue

        if model == 'location' and (str(obj.id), first_day) in visit_days:
            # The owner's visit on this place and date is already an event.
            continue

        if not _event_overlaps_range(first_day, last_day, range_start, range_end):
            continue
        start, end, all_day = first_day, last_day, True
        if item.start_time:
            start = _plan_clock(first_day, item.start_time, tz_name)
            end = _plan_clock(last_day, item.end_time, tz_name) if item.end_time else start
            if end < start:
                end = start
            all_day = False

        if model == 'location':
            category = obj.category
            events.append(_build_event(
                event_id=f'stop-{item.id}', event_type='stop', title=obj.name,
                start=start, end=end, all_day=all_day, timezone_name=tz_name if not all_day else None,
                icon=category.icon if category else '📍',
                category=category.name if category else 'Stop',
                location_label=obj.location or '', description=obj.description or '',
                url=f'/collections/{collection.id}', resource_id=str(obj.id), **common,
            ))
        elif model == 'note':
            events.append(_build_event(
                event_id=f'note-{obj.id}', event_type='note', title=obj.name,
                start=start, end=end, all_day=all_day, timezone_name=None, icon='📝',
                category='Note', description=obj.content or '',
                url=f'/collections/{collection.id}', resource_id=str(obj.id), **common,
            ))
        elif model == 'checklist':
            events.append(_build_event(
                event_id=f'checklist-{obj.id}', event_type='checklist', title=obj.name,
                start=start, end=end, all_day=all_day, timezone_name=None, icon='✅',
                category='Checklist', url=f'/collections/{collection.id}',
                resource_id=str(obj.id), **common,
            ))

    activities = Activity.objects.filter(
        day__collection_id__in=by_id.keys(), day__index__isnull=False
    ).select_related('day')
    for activity in activities:
        collection = by_id[activity.day.collection_id]
        day = projected_date(collection.start_date, activity.day.index)
        if not _event_overlaps_range(day, day, range_start, range_end):
            continue
        events.append(_build_event(
            event_id=f'activity-{activity.id}', event_type='activity', title=activity.name,
            start=day, end=day, all_day=True, timezone_name=None, icon='🥾',
            category=activity.sport_type or 'Activity', url=f'/collections/{collection.id}',
            resource_id=str(activity.id), collection_id=str(collection.id),
            collection_name=collection.name,
        ))
    return events


_EVENT_BUILDERS = {
    'visit': _visit_events,
    'transportation': _transportation_events,
    'lodging': _lodging_events,
    'collection': _collection_events,
    'note': _note_events,
    'checklist': _checklist_events,
}


def get_calendar_events_for_user(
    user,
    *,
    start: str | None = None,
    end: str | None = None,
    types: str | None = None,
) -> list[dict]:
    range_start = parse_iso_date(start)
    range_end = parse_iso_date(end)
    selected_types = _parse_types_param(types)

    events: list[dict] = []
    for event_type, builder in _EVENT_BUILDERS.items():
        if event_type in selected_types:
            events.extend(builder(user, range_start, range_end))
    events.extend(
        event for event in _plan_events(user, range_start, range_end)
        if event['type'] in selected_types
    )

    events.sort(key=lambda item: item.get('start') or '')
    return events


def iter_calendar_events_for_ics(user) -> Iterable[dict]:
    return get_calendar_events_for_user(user)
