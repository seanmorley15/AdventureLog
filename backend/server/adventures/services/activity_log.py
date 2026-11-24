"""
The collection activity feed: what changed, by whom.

Owners and editors read it. Membership changes are owner-only. It is never part of
the published story, and recording never blocks the change it describes.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def actor_for(request_or_user):
    """(user or None, display name) for a signed-in actor. Guests are named by their link."""
    user = getattr(request_or_user, 'user', request_or_user)
    if user is not None and getattr(user, 'is_authenticated', False):
        name = ' '.join(filter(None, [user.first_name, user.last_name])) or user.username
        return user, name
    return None, ''


def guest_actor(request, collection):
    """The guest link acting on ``collection``, if any."""
    from adventures.access.audience import audience_for_request

    audience = audience_for_request(request, collection) if hasattr(request, 'META') else None
    if audience and audience.guest_link is not None:
        return audience.guest_link
    return None


def record_activity(collection, request_or_user, verb, **data):
    from adventures.models import CollectionActivity

    try:
        user, name = actor_for(request_or_user)
        if user is None and hasattr(request_or_user, 'META'):
            link = guest_actor(request_or_user, collection)
            if link is not None:
                name = link.label or 'Guest'
        CollectionActivity.objects.create(
            collection=collection, verb=verb, actor_user=user, actor_name=name[:150], data=data
        )
    except Exception:  # pragma: no cover - the feed must never break an edit
        logger.exception('Could not record %s for collection %s', verb, getattr(collection, 'pk', None))


def visible_activity(collection, audience):
    """The feed an audience may read: none for viewers and readers, no membership for editors."""
    from adventures.models import CollectionActivity

    if audience is None or not audience.can_edit:
        return CollectionActivity.objects.none()
    qs = CollectionActivity.objects.filter(collection=collection)
    if not audience.is_owner:
        qs = qs.exclude(verb__in=CollectionActivity.OWNER_ONLY_VERBS)
    return qs.select_related('actor_user')
