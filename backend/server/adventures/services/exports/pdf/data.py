"""Loading a collection for the PDF, and grouping its records by day."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple
from django.db.models import Prefetch
from adventures.models import Checklist, ChecklistItem, Collection, CollectionItineraryItem, Location, Lodging

from .text import format_date, plain_text


def get_collection_for_pdf(collection_id) -> Collection:
    """Load a collection with relations needed for PDF export."""
    return (
        Collection.objects.filter(pk=collection_id)
        .select_related('primary_image', 'user')
        .prefetch_related(
            Prefetch(
                'locations',
                queryset=Location.objects.select_related(
                    'category', 'country', 'region', 'city'
                ).prefetch_related('visits'),
            ),
            'transportation_set',
            'note_set',
            Prefetch(
                'lodging_set',
                queryset=Lodging.objects.all(),
            ),
            Prefetch(
                'checklist_set',
                queryset=Checklist.objects.prefetch_related(
                    Prefetch('checklistitem_set', queryset=ChecklistItem.objects.order_by('name'))
                ),
            ),
            Prefetch(
                'itinerary_items',
                queryset=CollectionItineraryItem.objects.select_related('content_type').order_by(
                    'date', 'order'
                ),
            ),
            'itinerary_days',
        )
        .get()
    )


def trip_day_count(start: Optional[date], end: Optional[date]) -> Optional[int]:
    if not start or not end:
        return None
    return (end - start).days + 1


def _build_lookups(collection: Collection) -> Dict[str, Dict[str, Any]]:
    return {
        'location': {str(loc.id): loc for loc in collection.locations.all()},
        'transportation': {str(t.id): t for t in collection.transportation_set.all()},
        'lodging': {str(l.id): l for l in collection.lodging_set.all()},
        'note': {str(n.id): n for n in collection.note_set.all()},
        'checklist': {str(c.id): c for c in collection.checklist_set.all()},
    }


def resolve_item(
    itinerary_item: CollectionItineraryItem, lookups: Dict[str, Dict[str, Any]]
) -> Tuple[Optional[str], Optional[Any]]:
    model = itinerary_item.content_type.model
    obj = lookups.get(model, {}).get(str(itinerary_item.object_id))
    return model, obj


def _overnight_lodging_for_date(collection: Collection, day: date, scheduled_lodging_ids: set) -> List[Lodging]:
    result = []
    target = day
    for lodging in collection.lodging_set.all():
        if str(lodging.id) not in scheduled_lodging_ids:
            continue
        if not lodging.check_in or not lodging.check_out:
            continue
        check_in = lodging.check_in.date()
        check_out = lodging.check_out.date()
        if check_in <= target < check_out:
            result.append(lodging)
    return result


def _iter_trip_dates(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def placed_item_keys(collection: Collection) -> set:
    keys = set()
    for item in collection.itinerary_items.all():
        keys.add((item.content_type.model, str(item.object_id)))
    return keys


def is_day_plan(collection: Collection) -> bool:
    return collection.type == Collection.Type.TRIP and any(
        d.index is not None for d in collection.itinerary_days.all()
    )


def _group_indexed_days(collection: Collection) -> Tuple[List[Dict[str, Any]], List[CollectionItineraryItem], Dict[str, Dict[str, Any]]]:
    """A day plan: one section per day index. The date shows only when anchored."""
    lookups = _build_lookups(collection)
    days = sorted((d for d in collection.itinerary_days.all() if d.index is not None), key=lambda d: d.index)

    by_day: Dict[Any, List[CollectionItineraryItem]] = {}
    global_items: List[CollectionItineraryItem] = []
    spans: List[CollectionItineraryItem] = []
    index_by_day = {d.pk: d.index for d in days}
    for item in collection.itinerary_items.all():
        if item.is_global:
            global_items.append(item)
        elif item.day_id in index_by_day:
            by_day.setdefault(item.day_id, []).append(item)
            if item.content_type.model == 'lodging':
                spans.append(item)

    groups: List[Dict[str, Any]] = []
    for day in days:
        resolved = []
        for it in sorted(by_day.get(day.pk, []), key=lambda x: x.order):
            model, obj = resolve_item(it, lookups)
            if obj is not None:
                resolved.append({'order': it.order, 'type': model, 'object': obj})

        overnight = []
        for it in spans:
            start = index_by_day[it.day_id]
            end = it.span_end_index if it.span_end_index and it.span_end_index > start else start
            if start < day.index <= end:
                model, obj = resolve_item(it, lookups)
                if obj is not None:
                    overnight.append(obj)

        anchored_date = _projected_date(collection.start_date, day.index)
        label = f'Day {day.index}'
        if anchored_date:
            label = f'{label} · {format_date(anchored_date)}'
        groups.append(
            {
                'date': anchored_date,
                'display_date': label,
                'day_name': day.name or None,
                'day_description': plain_text(day.description) if day.description else None,
                'items': resolved,
                'overnight_lodging': overnight,
            }
        )
    return groups, global_items, lookups


def _projected_date(anchor: Optional[date], index: int) -> Optional[date]:
    return anchor + timedelta(days=index - 1) if anchor else None


def group_itinerary_days(collection: Collection) -> Tuple[List[Dict[str, Any]], List[CollectionItineraryItem], Dict[str, Dict[str, Any]]]:
    """Mirror the web planner: one section per day."""
    if is_day_plan(collection):
        return _group_indexed_days(collection)
    lookups = _build_lookups(collection)
    day_meta = {d.date: d for d in collection.itinerary_days.all()}

    dated_items: Dict[date, List[CollectionItineraryItem]] = {}
    global_items: List[CollectionItineraryItem] = []
    scheduled_lodging_ids = set()

    for item in collection.itinerary_items.all():
        model = item.content_type.model
        if model == 'lodging':
            scheduled_lodging_ids.add(str(item.object_id))
        if item.is_global:
            global_items.append(item)
        elif item.date:
            dated_items.setdefault(item.date, []).append(item)

    for items in dated_items.values():
        items.sort(key=lambda x: x.order)

    start = collection.start_date
    end = collection.end_date
    if not start or not end:
        if dated_items:
            dates = sorted(dated_items.keys())
            start = dates[0]
            end = dates[-1]
        else:
            return []

    days: List[Dict[str, Any]] = []
    for day in _iter_trip_dates(start, end):
        resolved = []
        for it in dated_items.get(day, []):
            model, obj = resolve_item(it, lookups)
            if obj is not None:
                resolved.append({'order': it.order, 'type': model, 'object': obj})

        overnight = _overnight_lodging_for_date(collection, day, scheduled_lodging_ids)
        meta = day_meta.get(day)
        days.append(
            {
                'date': day,
                'display_date': format_date(day),
                'day_name': meta.name if meta and meta.name else None,
                'day_description': plain_text(meta.description) if meta and meta.description else None,
                'items': resolved,
                'overnight_lodging': overnight,
            }
        )
    return days, global_items, lookups


def _replace_prefetched(obj, name, items) -> None:
    cache = getattr(obj, '_prefetched_objects_cache', {})
    if name in cache:
        cache[name]._result_cache = list(items)


def apply_story_groups(collection: Collection) -> None:
    """
    Redact the loaded records in memory for a public reader. Nothing is saved.

    Uses the same groups as the story payload: costs, reservations, lodging
    address, coordinates, note text, and checklist text, all off until the
    owner turns them on. Private notes and checklist items stay hidden.
    """
    def on(name):
        return collection.story_group(name)

    for location in collection.locations.all():
        location._story_hide_visits = True
        location.category = None
        if not location.is_public and not on('place_details'):
            location.description = None
            location.link = None
            location.rating = None
        if not on('coordinates'):
            location.location = None
            location.city = None
            location.region = None
            location.country = None
        if not on('costs'):
            location.price = None
    for transport in collection.transportation_set.all():
        if not on('reservations'):
            transport.flight_number = None
            transport.link = None
        if not on('costs'):
            transport.price = None
        if not on('note_text'):
            transport.description = None
    for lodging in collection.lodging_set.all():
        if not on('reservations'):
            lodging.reservation_number = None
            lodging.link = None
        if not on('costs'):
            lodging.price = None
        if not on('note_text'):
            lodging.description = None
        if not on('lodging_address'):
            lodging.location = None
    notes = [note for note in collection.note_set.all() if not note.is_private]
    for note in notes:
        if not on('note_text'):
            note.content = None
            note.links = None
    _replace_prefetched(collection, 'note_set', notes)
    for checklist in collection.checklist_set.all():
        items = [] if not on('checklist_text') else [
            item for item in checklist.checklistitem_set.all() if not item.is_private
        ]
        _replace_prefetched(checklist, 'checklistitem_set', items)
