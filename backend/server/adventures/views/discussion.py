"""Comments and the activity feed for a collection. Rules live in services/discussion.py."""
from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from adventures.models import (
    Collection,
    CollectionActivity,
    CollectionComment,
    CollectionItineraryDay,
    CollectionItineraryItem,
    CommentInboxState,
)
from adventures.services.activity_log import record_activity, visible_activity
from adventures.access.audience import audience_for_request
from adventures.services.discussion import (
    MAX_BODY,
    author_fields,
    can_moderate,
    can_post,
    can_read_thread,
    inbox_queryset,
    is_author,
    notify_mentions,
    person_summary,
    resolve_mentions,
    serialize_comment,
    thread_payload,
)

THREADS = {'plan': False, 'story': True}


def _collection(collection_id):
    try:
        return Collection.objects.get(pk=collection_id)
    except (Collection.DoesNotExist, ValueError, TypeError, ValidationError):
        raise NotFound('Collection not found.')
    except Exception:
        raise NotFound('Collection not found.')


def _thread(value):
    if value not in THREADS:
        raise ValidationError({'thread': 'Use "plan" or "story".'})
    return THREADS[value]


def _body(value):
    body = (value or '').strip()
    if not body:
        raise ValidationError({'body': 'Write something first.'})
    if len(body) > MAX_BODY:
        raise ValidationError({'body': f'Keep it under {MAX_BODY} characters.'})
    return body


class CollectionCommentViewSet(viewsets.ViewSet):
    """
    /api/collection-comments/?collection=<id>&thread=plan|story

    Access is decided per thread, not by the collection permission class, so guest
    editors and signed-in story readers can post without owning the collection.
    """

    permission_classes = [AllowAny]

    def _get_comment(self, request, pk):
        comment = (
            CollectionComment.objects.select_related('collection', 'author_user', 'day')
            .filter(pk=pk)
            .first()
        )
        if comment is None or not can_read_thread(request, comment.collection, comment.is_story):
            raise NotFound('Comment not found.')
        return comment

    def list(self, request):
        collection = _collection(request.query_params.get('collection'))
        is_story = _thread(request.query_params.get('thread', 'plan'))
        if not can_read_thread(request, collection, is_story):
            raise NotFound('Collection not found.')
        return Response({
            'thread': 'story' if is_story else 'plan',
            'comment_access': collection.comment_access,
            'can_post': can_post(request, collection, is_story),
            'comments': thread_payload(collection, request, is_story),
        })

    @transaction.atomic
    def create(self, request):
        collection = _collection(request.data.get('collection'))
        is_story = _thread(request.data.get('thread', 'plan'))
        if not can_read_thread(request, collection, is_story):
            raise NotFound('Collection not found.')
        if not can_post(request, collection, is_story):
            raise PermissionDenied('You cannot comment here.')
        author = author_fields(request, collection)
        if author is None:
            raise PermissionDenied('Sign in to comment.')
        body = _body(request.data.get('body'))

        parent = None
        if request.data.get('parent'):
            parent = CollectionComment.objects.filter(
                pk=request.data['parent'], collection=collection, is_story=is_story
            ).first()
            if parent is None:
                raise ValidationError({'parent': 'That comment is not in this thread.'})
            # Replies are one level deep: a reply to a reply joins the same thread.
            if parent.parent_id:
                parent = parent.parent

        day = placement = None
        if not is_story:
            if request.data.get('day'):
                day = CollectionItineraryDay.objects.filter(pk=request.data['day'], collection=collection).first()
                if day is None:
                    raise ValidationError({'day': 'That day is not in this collection.'})
            if request.data.get('placement'):
                placement = CollectionItineraryItem.objects.filter(
                    pk=request.data['placement'], collection=collection
                ).first()
                if placement is None:
                    raise ValidationError({'placement': 'That item is not in this collection.'})
                day = day or placement.day
        if parent is not None:
            day, placement = parent.day, parent.placement

        comment = CollectionComment.objects.create(
            collection=collection,
            is_story=is_story,
            parent=parent,
            day=day,
            placement=placement,
            body=body,
            **author,
        )
        mentioned = resolve_mentions(collection, body) if not is_story else []
        if mentioned:
            comment.mentions.set(mentioned)
        record_activity(
            collection,
            request,
            CollectionActivity.Verb.COMMENT_ADDED,
            comment=str(comment.pk),
            thread='story' if is_story else 'plan',
            day_index=day.index if day else None,
            excerpt=body[:140],
        )
        page = request.build_absolute_uri(f'/collections/{collection.pk}') if mentioned else None
        transaction.on_commit(lambda: notify_mentions(comment, mentioned, page))
        return Response(serialize_comment(comment, request, story=is_story), status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        comment = self._get_comment(request, pk)
        if not is_author(request, comment):
            raise PermissionDenied('You can only edit your own comments.')
        comment.body = _body(request.data.get('body'))
        comment.edited_at = timezone.now()
        comment.save(update_fields=['body', 'edited_at'])
        if not comment.is_story:
            comment.mentions.set(resolve_mentions(comment.collection, comment.body))
        return Response(serialize_comment(comment, request, story=comment.is_story))

    def destroy(self, request, pk=None):
        comment = self._get_comment(request, pk)
        if not (is_author(request, comment) or can_moderate(request, comment)):
            raise PermissionDenied('You can only delete your own comments.')
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='inbox')
    def inbox(self, request):
        """
        New comments for the signed-in user: the private plans they belong to, and the
        stories they own. Their own comments are left out.
        """
        if not request.user.is_authenticated:
            raise PermissionDenied('Sign in to see new comments.')
        user = request.user
        state = CommentInboxState.objects.filter(user=user).first()
        seen_at = state.seen_at if state else None
        qs = (
            inbox_queryset(user)
            .select_related('collection', 'author_user', 'day')
            .prefetch_related('mentions')
            .order_by('-created_at')
        )
        try:
            limit = max(1, min(int(request.query_params.get('limit', 30)), 100))
        except (TypeError, ValueError):
            limit = 30
        items = []
        for comment in qs[:limit]:
            items.append({
                'id': str(comment.pk),
                'collection': {'id': str(comment.collection_id), 'name': comment.collection.name},
                'thread': 'story' if comment.is_story else 'plan',
                'day_index': comment.day.index if comment.day_id else None,
                'author_name': comment.author_name,
                'author': {'name': comment.author_name, **person_summary(comment.author_user, user)},
                'excerpt': comment.body[:200],
                'created_at': comment.created_at,
                'mentions_me': any(u.pk == user.pk for u in comment.mentions.all()),
                'unread': seen_at is None or comment.created_at > seen_at,
            })
        unread = qs.filter(created_at__gt=seen_at).count() if seen_at else qs.count()
        return Response({'unread_count': unread, 'comments': items})

    @action(detail=False, methods=['post'], url_path='inbox/seen')
    def inbox_seen(self, request):
        if not request.user.is_authenticated:
            raise PermissionDenied('Sign in to see new comments.')
        CommentInboxState.objects.update_or_create(user=request.user, defaults={'seen_at': timezone.now()})
        return Response({'unread_count': 0})


class CollectionActivityViewSet(viewsets.ViewSet):
    """/api/collection-activity/?collection=<id> — owners and editors; membership events owner-only."""

    permission_classes = [AllowAny]

    def list(self, request):
        collection = _collection(request.query_params.get('collection'))
        audience = audience_for_request(request, collection)
        if audience is None or not audience.is_member:
            raise NotFound('Collection not found.')
        if not audience.can_edit:
            raise PermissionDenied('Viewers do not see the activity feed.')
        try:
            limit = max(1, min(int(request.query_params.get('limit', 50)), 200))
        except (TypeError, ValueError):
            limit = 50
        events = visible_activity(collection, audience)[:limit]
        return Response([
            {
                'id': str(event.pk),
                'verb': event.verb,
                'actor_name': event.actor_name,
                'actor': person_summary(event.actor_user, request.user),
                'data': event.data,
                'created_at': event.created_at,
            }
            for event in events
        ])
