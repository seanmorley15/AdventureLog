"""
Who is looking at a collection, and what they may do.

One function resolves the audience. Views, serializers, PDF, ICS, and media
call it instead of reading ``is_public`` or ``shared_with`` directly.

- ``owner``: everything, including members, visibility, and delete.
- ``editor``: changes days, placements, notes, checklists, lodging, transport,
  day files, and the anchor. Not members, visibility, or delete.
- ``viewer``: reads the private plan. Changes nothing.
- A guest link carries the ``editor`` or ``viewer`` role for someone with no
  account. A guest has no personal calendar.
- ``public``: visibility is public, or unlisted with the link secret. Receives
  the story payload only.

Member and guest access never reads ``is_public``.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Q
from django.utils import timezone

OWNER = 'owner'
EDITOR = 'editor'
VIEWER = 'viewer'
PUBLIC = 'public'

GUEST_TOKEN_HEADER = 'HTTP_X_GUEST_TOKEN'
# Set by the frontend when someone opens a guest link; media requests carry it.
GUEST_COOKIE = 'adventurelog_guest'
STORY_SECRET_HEADER = 'HTTP_X_STORY_SECRET'
STORY_SECRET_PARAM = 's'


@dataclass(frozen=True)
class Audience:
    role: str
    guest_link: object = None

    @property
    def is_owner(self):
        return self.role == OWNER

    @property
    def can_edit(self):
        return self.role in (OWNER, EDITOR)

    @property
    def is_member(self):
        """Sees the private plan: owner, editor, viewer, or a guest link."""
        return self.role in (OWNER, EDITOR, VIEWER)

    @property
    def is_guest(self):
        return self.guest_link is not None

    @property
    def is_public_reader(self):
        return self.role == PUBLIC

    def as_dict(self):
        return {
            'role': self.role,
            'is_owner': self.is_owner,
            'can_edit': self.can_edit,
            'is_member': self.is_member,
            'is_guest': self.is_guest,
        }


def _user(user):
    if user is None or not getattr(user, 'is_authenticated', False):
        return None
    return user


def guest_token_from_request(request):
    if request is None:
        return None
    meta = getattr(request, 'META', {})
    token = meta.get(GUEST_TOKEN_HEADER) or getattr(request, 'COOKIES', {}).get(GUEST_COOKIE)
    if not token:
        params = getattr(request, 'query_params', None) or getattr(request, 'GET', {})
        token = params.get('guest')
    return token or None


def story_secret_from_request(request):
    if request is None:
        return None
    params = getattr(request, 'query_params', None) or getattr(request, 'GET', {})
    return params.get(STORY_SECRET_PARAM) or getattr(request, 'META', {}).get(STORY_SECRET_HEADER) or None


def active_guest_links():
    from adventures.models import CollectionGuestLink

    now = timezone.now()
    return CollectionGuestLink.objects.filter(revoked_at__isnull=True).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    )


def guest_link_for(token, collection=None):
    if not token:
        return None
    links = active_guest_links().filter(token=token)
    if collection is not None:
        links = links.filter(collection_id=collection.pk)
    return links.select_related('collection').first()


def member_role(collection, user):
    """owner, editor, viewer, or None. A shared_with user with no role row is an editor."""
    from adventures.models import CollectionMember

    user = _user(user)
    if collection is None or user is None:
        return None
    if collection.user_id == user.id:
        return OWNER
    if not collection.shared_with.filter(id=user.id).exists():
        return None
    role = (
        CollectionMember.objects.filter(collection_id=collection.pk, user_id=user.id)
        .values_list('role', flat=True)
        .first()
    )
    return role or EDITOR


def resolve_audience(collection, user=None, *, guest_token=None, story_secret=None):
    """The audience for this collection, or None when there is no access."""
    from adventures.models import Collection

    if collection is None:
        return None
    role = member_role(collection, user)
    if role is not None:
        return Audience(role)
    link = guest_link_for(guest_token, collection)
    if link is not None:
        return Audience(link.role, guest_link=link)
    if collection.visibility == Collection.Visibility.PUBLIC:
        return Audience(PUBLIC)
    if (
        collection.visibility == Collection.Visibility.UNLISTED
        and story_secret
        and story_secret == collection.share_secret
    ):
        return Audience(PUBLIC)
    return None


def audience_for_request(request, collection):
    """Resolve once per request and collection."""
    if collection is None:
        return None
    cache = getattr(request, '_collection_audience', None)
    if cache is None:
        cache = {}
        try:
            request._collection_audience = cache
        except AttributeError:
            pass
    key = collection.pk
    if key not in cache:
        cache[key] = resolve_audience(
            collection,
            getattr(request, 'user', None),
            guest_token=guest_token_from_request(request),
            story_secret=story_secret_from_request(request),
        )
    return cache[key]


def can_edit(request_or_user, collection):
    """Owner, editor, or guest editor."""
    audience = _audience(request_or_user, collection)
    return bool(audience and audience.can_edit)


def is_member(request_or_user, collection):
    """Owner, editor, viewer, or guest: sees the private plan."""
    audience = _audience(request_or_user, collection)
    return bool(audience and audience.is_member)


def _audience(request_or_user, collection):
    if collection is None:
        return None
    if hasattr(request_or_user, 'META'):
        return audience_for_request(request_or_user, collection)
    role = member_role(collection, request_or_user)
    return Audience(role) if role else None


def member_collections_q(request_or_user, prefix='', *, editable=False):
    """
    Q matching collections the requester is a member of (or holds a guest link to).
    ``prefix`` is the path to the collection, e.g. ``'collection__'``.
    """
    from adventures.models import CollectionMember

    user = request_or_user if not hasattr(request_or_user, 'META') else getattr(request_or_user, 'user', None)
    user = _user(user)
    q = Q(pk__in=[])
    if user is not None:
        owned = Q(**{f'{prefix}user': user})
        shared = Q(**{f'{prefix}shared_with': user})
        if editable:
            viewer_of = CollectionMember.objects.filter(user=user, role=VIEWER).values('collection_id')
            shared &= ~Q(**{f'{prefix}pk__in': viewer_of})
        q = owned | shared
    if hasattr(request_or_user, 'META'):
        link = guest_link_for(guest_token_from_request(request_or_user))
        if link is not None and (not editable or link.role == EDITOR):
            q |= Q(**{f'{prefix}pk': link.collection_id})
    return q


def has_guest_token(request):
    return guest_link_for(guest_token_from_request(request)) is not None


def readable_collections_q(request):
    """Collections this request may open: membership, a guest link, or the story."""
    from adventures.models import Collection

    q = member_collections_q(request) | Q(visibility=Collection.Visibility.PUBLIC)
    secret = story_secret_from_request(request)
    if secret:
        q |= Q(visibility=Collection.Visibility.UNLISTED, share_secret=secret)
    return q
