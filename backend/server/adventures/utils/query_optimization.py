"""
Shared select_related / prefetch_related sets for the serializers.

``LocationSerializer`` and its nested serializers read a place's owner, category,
place hierarchy, photos, attachments, trails, visits (with activities) and linked
collections. Loading those up front turns hundreds of per-row queries into a fixed
handful. Keep this in sync with what the serializers read.
"""
from django.db.models import Prefetch

from adventures.models import Activity, ContentAttachment, ContentImage, Trail

LOCATION_SELECT_RELATED = (
    'user',
    'category__user',
    'country',
    'region__country',
    'city__region__country',
)


def location_prefetches():
    return [
        Prefetch('images', queryset=ContentImage.objects.select_related('user')),
        Prefetch('attachments', queryset=ContentAttachment.objects.select_related('user')),
        Prefetch('trails', queryset=Trail.objects.select_related('user')),
        Prefetch('visits__activities', queryset=Activity.objects.select_related('user')),
        'collections',
    ]


def optimize_locations(queryset):
    """Apply the full load set to a Location queryset that will be serialized."""
    return queryset.select_related(*LOCATION_SELECT_RELATED).prefetch_related(*location_prefetches())


def media_prefetches():
    """Photos and attachments of lodging and transportation, with their owners."""
    return [
        Prefetch('images', queryset=ContentImage.objects.select_related('user')),
        Prefetch('attachments', queryset=ContentAttachment.objects.select_related('user')),
    ]
