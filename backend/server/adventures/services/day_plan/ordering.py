"""Order and bucket primitives: numbering rows in a day, Ideas, or the trip-wide group."""

from __future__ import annotations


from django.db.models import Max

from .constants import TEMP_ORDER_OFFSET


def lock(collection):
    from adventures.models import Collection

    return Collection.objects.select_for_update().get(pk=collection.pk)

def renumber(days):
    """Two-phase index write so the partial unique index never collides."""
    from adventures.models import CollectionItineraryDay

    for offset, day in enumerate(days):
        day.index = TEMP_ORDER_OFFSET + offset
    CollectionItineraryDay.objects.bulk_update(days, ['index'])
    for position, day in enumerate(days, start=1):
        day.index = position
    CollectionItineraryDay.objects.bulk_update(days, ['index'])

def next_order(collection, *, day=None, is_global=False):
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

def spanning_items(collection):
    from adventures.models import CollectionItineraryItem

    return list(
        CollectionItineraryItem.objects.filter(
            collection=collection, day__isnull=False, span_end_index__isnull=False
        ).select_related('day', 'content_type')
    )

def save_spans(items):
    from adventures.models import CollectionItineraryItem

    for item in items:
        if item.span_end_index is not None and item.day_id and item.span_end_index <= item.day.index:
            item.span_end_index = None
    if items:
        CollectionItineraryItem.objects.bulk_update(items, ['day', 'span_end_index'])

def day_blocking_items(collection, day):
    """Items that start on ``day`` and do not continue onto a later day."""
    from adventures.models import CollectionItineraryItem

    return [
        item
        for item in CollectionItineraryItem.objects.filter(collection=collection, day=day).select_related('day', 'content_type')
        if not (item.span_end_index and item.span_end_index > day.index)
    ]

def place_after_existing(collection, day, items):
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

def _bucket_queryset(collection, *, day=None, is_global=False):
    from adventures.models import CollectionItineraryItem

    qs = CollectionItineraryItem.objects.filter(collection=collection)
    if day is not None:
        return qs.filter(day=day)
    if is_global:
        return qs.filter(is_global=True)
    return qs.filter(day__isnull=True, is_global=False, date__isnull=True)

def reorder_bucket(collection, item, position):
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

def compact_bucket(collection, day_id, is_global):
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
