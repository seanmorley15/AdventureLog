from __future__ import annotations

from datetime import date, datetime, timedelta, timezone as dt_timezone
from typing import Iterable

from django.db.models import Prefetch, Q
from django.utils import timezone

from adventures.models import (
    Checklist,
    Collection,
    Location,
    Lodging,
    Note,
    Transportation,
    Visit,
)

CALENDAR_EVENT_COLORS = {
    'visit': '#3b82f6',
    'transportation': '#f97316',
    'lodging': '#8b5cf6',
    'collection': '#10b981',
    'note': '#6366f1',
    'checklist': '#14b8a6',
}

ALL_EVENT_TYPES = tuple(CALENDAR_EVENT_COLORS.keys())


def _parse_date_param(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _parse_types_param(value: str | None) -> set[str]:
    if not value:
        return set(ALL_EVENT_TYPES)
    requested = {item.strip().lower() for item in value.split(',') if item.strip()}
    return requested & set(ALL_EVENT_TYPES) or set(ALL_EVENT_TYPES)


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


def _is_midnight_utc(value: datetime) -> bool:
    if timezone.is_naive(value):
        value = timezone.make_aware(value, dt_timezone.utc)
    utc_value = value.astimezone(dt_timezone.utc)
    return (
        utc_value.hour == 0
        and utc_value.minute == 0
        and utc_value.second == 0
        and utc_value.microsecond == 0
    )


def _visit_events(
    user,
    range_start: date | None,
    range_end: date | None,
) -> list[dict]:
    events: list[dict] = []
    locations = (
        Location.objects.filter(
            Q(user=user.id)
            | Q(collections__shared_with=user.id)
            | Q(is_public=True)
        )
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
        collection = location.collections.first()
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

            all_day = _is_midnight_utc(visit.start_date)
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
    transportations = (
        Transportation.objects.filter(
            Q(user=user.id) | Q(collection__shared_with=user.id)
        )
        .select_related('collection')
        .distinct()
    )

    transport_icons = {
        'flight': '✈️',
        'train': '🚆',
        'bus': '🚌',
        'car': '🚗',
        'boat': '🚢',
    }

    for item in transportations:
        if not item.date:
            continue
        if not _event_overlaps_range(item.date, item.end_date or item.date, range_start, range_end):
            continue

        route = ' → '.join(filter(None, [item.from_location, item.to_location]))
        icon = transport_icons.get((item.type or '').lower(), '🛣️')
        collection_id = str(item.collection_id) if item.collection_id else None

        events.append(
            _build_event(
                event_id=f'transportation-{item.id}',
                event_type='transportation',
                title=item.name or item.type or 'Transportation',
                start=item.date,
                end=item.end_date or item.date,
                all_day=_is_midnight_utc(item.date),
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
    stays = (
        Lodging.objects.filter(Q(user=user.id) | Q(collection__shared_with=user.id))
        .select_related('collection')
        .distinct()
    )

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
    collections = Collection.objects.filter(
        Q(user=user.id) | Q(shared_with=user.id)
    ).distinct()

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
    notes = (
        Note.objects.filter(Q(user=user.id) | Q(collection__shared_with=user.id))
        .filter(date__isnull=False)
        .select_related('collection')
        .distinct()
    )

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
    checklists = (
        Checklist.objects.filter(Q(user=user.id) | Q(collection__shared_with=user.id))
        .filter(date__isnull=False)
        .select_related('collection')
        .distinct()
    )

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
    range_start = _parse_date_param(start)
    range_end = _parse_date_param(end)
    selected_types = _parse_types_param(types)

    events: list[dict] = []
    for event_type in ALL_EVENT_TYPES:
        if event_type not in selected_types:
            continue
        builder = _EVENT_BUILDERS[event_type]
        events.extend(builder(user, range_start, range_end))

    events.sort(key=lambda item: item.get('start') or '')
    return events


def iter_calendar_events_for_ics(user) -> Iterable[dict]:
    return get_calendar_events_for_user(user)
