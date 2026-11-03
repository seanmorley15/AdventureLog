"""
Link and unlink a place from a collection.

A place can sit in many collections. These helpers change one membership at a
time, so callers never rewrite the whole list and drop links they can't see.
"""
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from adventures.models import CollectionItineraryItem, Location


def _placements_qs(location, collection):
    ct = ContentType.objects.get_for_model(Location)
    return CollectionItineraryItem.objects.filter(
        collection=collection, content_type=ct, object_id=location.pk
    )


def placements_for(location, collection):
    """Plan placements of this place in this collection: [{day_index, is_global}]."""
    rows = _placements_qs(location, collection).select_related('day')
    return [
        {'day_index': row.day.index if row.day_id else None, 'is_global': row.is_global}
        for row in rows
    ]


def link_location(location, collection):
    """Add the membership. Idempotent."""
    location.collections.add(collection)


def unlink_location(location, collection):
    """
    Remove the membership and every plan placement of the place in that
    collection, together. Returns how many placements were removed.
    """
    with transaction.atomic():
        placements = _placements_qs(location, collection)
        removed = placements.count()
        placements.delete()
        location.collections.remove(collection)
    return removed
