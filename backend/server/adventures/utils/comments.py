"""
Comments on a collection.

Two threads that never mix:

- The private plan (``is_story=False``): members read it; the owner and editors
  (including guest editors) write. Viewers read and do not write.
- The published story (``is_story=True``): readable with the story once the owner
  turns comments on. ``comment_access`` decides who writes: ``signed_in`` lets any
  signed-in reader comment, ``link_holders`` also lets guest links comment. Nobody
  comments anonymously, and nothing comments while the story is private.

``@username`` mentions resolve to current members only, on the private plan.
"""
from __future__ import annotations

import logging
import re

from django.conf import settings
from django.core.mail import send_mail

from adventures.utils.audience import audience_for_request

logger = logging.getLogger(__name__)

MENTION_PATTERN = re.compile(r'(?<![\w@])@([\w.+-]{1,150})')
MAX_BODY = 4000


def _signed_in(request):
    user = getattr(request, 'user', None)
    return bool(user and user.is_authenticated)


def can_read_thread(request, collection, is_story):
    audience = audience_for_request(request, collection)
    if audience is None:
        return False
    if not is_story:
        return audience.is_member
    if audience.is_member:
        return True
    return collection.visibility != collection.Visibility.PRIVATE and comments_open(collection)


def comments_open(collection):
    return (
        collection.comment_access != collection.CommentAccess.OFF
        and collection.visibility != collection.Visibility.PRIVATE
    )


def can_post(request, collection, is_story):
    audience = audience_for_request(request, collection)
    if audience is None:
        return False
    if not is_story:
        return audience.can_edit
    if not comments_open(collection):
        return False
    if _signed_in(request):
        return True
    return (
        collection.comment_access == collection.CommentAccess.LINK_HOLDERS
        and audience.guest_link is not None
    )


def is_author(request, comment):
    if _signed_in(request):
        return comment.author_user_id == request.user.id
    audience = audience_for_request(request, comment.collection)
    return bool(
        audience and audience.guest_link is not None and comment.author_guest_id == audience.guest_link.pk
    )


def can_moderate(request, comment):
    return _signed_in(request) and comment.collection.user_id == request.user.id


def author_fields(request, collection):
    """author_user, author_guest, author_name for a new comment. None when anonymous."""
    if _signed_in(request):
        user = request.user
        name = ' '.join(filter(None, [user.first_name, user.last_name])) or user.username
        return {'author_user': user, 'author_guest': None, 'author_name': name[:150]}
    audience = audience_for_request(request, collection)
    if audience and audience.guest_link is not None:
        link = audience.guest_link
        return {'author_user': None, 'author_guest': link, 'author_name': (link.label or 'Guest')[:150]}
    return None


def resolve_mentions(collection, body):
    """Members named with @username. Anyone else is left as plain text."""
    from users.models import CustomUser

    names = {match.lower() for match in MENTION_PATTERN.findall(body or '')}
    if not names:
        return []
    member_ids = [collection.user_id, *collection.shared_with.values_list('id', flat=True)]
    return [
        user for user in CustomUser.objects.filter(id__in=member_ids)
        if user.username.lower() in names
    ]


def smtp_configured():
    """Mail is sent only when the server already has SMTP (not the console backend)."""
    return bool(getattr(settings, 'SMTP_CONFIGURED', False))


def notify_mentions(comment, users, page_url=None):
    """Email mentioned members, only when the server already has SMTP set up."""
    if not users or not smtp_configured():
        return 0
    sent = 0
    for user in users:
        if not user.email or user.id == comment.author_user_id:
            continue
        lines = [
            f'{comment.author_name or "Someone"} mentioned you in {comment.collection.name}:',
            '',
            comment.body,
        ]
        if page_url:
            lines += ['', page_url]
        try:
            sent += send_mail(
                subject=f'{getattr(settings, "INVITATIONS_EMAIL_SUBJECT_PREFIX", "")}'
                f'New mention in {comment.collection.name}',
                message='\n'.join(lines),
                from_email=None,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:  # pragma: no cover - mail must never block a comment
            logger.exception('Could not email mention for comment %s', comment.pk)
    return sent


def person_summary(user, viewer=None, *, only_public=False):
    """
    How a signed-in person is shown next to a comment or activity entry.

    ``can_view_profile`` is true when their profile page opens for the viewer: it is
    public, or it is the viewer's own. ``only_public`` hides the username and picture of
    people whose profile is private (used on the public story).
    """
    from adventures.serializers import _build_profile_pic_url

    if user is None:
        return {'username': None, 'uuid': None, 'profile_pic': None, 'can_view_profile': False}
    is_public = bool(getattr(user, 'public_profile', False))
    is_me = bool(viewer is not None and getattr(viewer, 'is_authenticated', False) and viewer.pk == user.pk)
    if only_public and not is_public:
        return {'username': None, 'uuid': None, 'profile_pic': None, 'can_view_profile': False}
    return {
        'username': user.username,
        'uuid': str(user.uuid),
        'profile_pic': _build_profile_pic_url(user),
        'can_view_profile': is_public or is_me,
    }


def inbox_queryset(user):
    """
    Comments a user may want to see: the private plans they belong to and the stories
    they own. Their own comments are left out.
    """
    from django.db.models import Q

    from adventures.models import Collection, CollectionComment

    member_of = Collection.objects.filter(shared_with=user).values('pk')
    owned = Collection.objects.filter(user=user).values('pk')
    return CollectionComment.objects.filter(
        Q(collection__in=owned) | Q(collection__in=member_of, is_story=False)
    ).exclude(author_user=user)


def unread_comment_count(user):
    """How many inbox comments are newer than the user's last visit to the inbox."""
    from adventures.models import CommentInboxState

    seen_at = CommentInboxState.objects.filter(user=user).values_list('seen_at', flat=True).first()
    qs = inbox_queryset(user)
    return qs.filter(created_at__gt=seen_at).count() if seen_at else qs.count()


def serialize_comment(comment, request, *, story=False):
    """
    A comment as the client sees it. On the story, an author's username and picture
    show only when their profile is public, and the comment's day stays a number.
    """
    user = comment.author_user
    viewer = getattr(request, 'user', None)
    person = person_summary(user, viewer, only_public=story)
    data = {
        'id': str(comment.id),
        'is_story': comment.is_story,
        'parent': str(comment.parent_id) if comment.parent_id else None,
        'day_index': comment.day.index if comment.day_id else None,
        'body': comment.body,
        'created_at': comment.created_at,
        'edited_at': comment.edited_at,
        'author': {
            'name': comment.author_name,
            **person,
            'is_guest': user is None,
        },
        'can_edit': is_author(request, comment),
        'can_delete': is_author(request, comment) or can_moderate(request, comment),
    }
    if not story:
        data['day'] = str(comment.day_id) if comment.day_id else None
        data['placement'] = str(comment.placement_id) if comment.placement_id else None
        data['mentions'] = [u.username for u in comment.mentions.all()]
    return data


def thread_payload(collection, request, is_story):
    """Top-level comments, oldest first, each with its replies."""
    from adventures.models import CollectionComment

    comments = list(
        CollectionComment.objects.filter(collection=collection, is_story=is_story)
        .select_related('author_user', 'day', 'collection')
        .prefetch_related('mentions')
    )
    replies = {}
    for comment in comments:
        if comment.parent_id:
            replies.setdefault(comment.parent_id, []).append(comment)
    return [
        {
            **serialize_comment(comment, request, story=is_story),
            'replies': [serialize_comment(r, request, story=is_story) for r in replies.get(comment.pk, [])],
        }
        for comment in comments
        if comment.parent_id is None
    ]
