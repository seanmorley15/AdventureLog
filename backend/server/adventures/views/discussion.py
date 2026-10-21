"""Comments and the activity feed for a collection. Rules live in services/discussion.py."""
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from adventures.models import (
    CollectionActivity,
    CollectionComment,
    CollectionItineraryDay,
    CollectionItineraryItem,
    CommentInboxState,
)
from adventures.serializers.discussion import (
    ActivityEventSerializer,
    ActivityFeedQuerySerializer,
    CommentCreateSerializer,
    CommentSerializer,
    CommentThreadSerializer,
    CommentUpdateSerializer,
    InboxQuerySerializer,
    InboxSerializer,
    ThreadQuerySerializer,
    UnreadCountSerializer,
)
from adventures.services.activity_log import record_activity, visible_activity
from adventures.access.audience import audience_for_request
from adventures.services.discussion import (
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
from adventures.views.mixins import COLLECTION_ID_PARAMETER, CollectionScopedMixin
from core.parsing import as_uuid
from core.serializers import validated


@extend_schema(parameters=[COLLECTION_ID_PARAMETER])
class CollectionCommentViewSet(CollectionScopedMixin, viewsets.ViewSet):
    """
    Comments on a collection: the members' `plan` thread and the public `story` thread.

    Access is decided per thread, not by collection role alone, so guest editors and
    signed-in story readers can comment where the owner allows it. Collections you cannot
    see answer 404.
    """

    openapi_tags = ['Comments']
    permission_classes = [AllowAny]

    @extend_schema(parameters=[ThreadQuerySerializer], responses=CommentThreadSerializer)
    def list(self, request, collection_id=None):
        """
        List a thread's comments

        Top-level comments oldest first, each with its replies, and whether you can post.
        """
        params = validated(ThreadQuerySerializer, request.query_params)
        collection = self.get_collection()
        is_story = params['thread'] == 'story'
        if not can_read_thread(request, collection, is_story):
            raise NotFound('Collection not found.')
        return Response({
            'thread': params['thread'],
            'comment_access': collection.comment_access,
            'can_post': can_post(request, collection, is_story),
            'comments': thread_payload(collection, request, is_story),
        })

    @extend_schema(request=CommentCreateSerializer, responses={201: CommentSerializer})
    @transaction.atomic
    def create(self, request, collection_id=None):
        """
        Post a comment

        Replies are one level deep: a reply to a reply joins the same thread. Mentioned
        members are notified by email.
        """
        params = validated(CommentCreateSerializer, request.data)
        collection = self.get_collection()
        is_story = params['thread'] == 'story'
        if not can_read_thread(request, collection, is_story):
            raise NotFound('Collection not found.')
        if not can_post(request, collection, is_story):
            raise PermissionDenied('You cannot comment here.')
        author = author_fields(request, collection)
        if author is None:
            raise PermissionDenied('Sign in to comment.')
        body = params['body'].strip()
        if not body:
            raise ValidationError({'body': ['Write something first.']})

        parent = None
        if params.get('parent'):
            parent = CollectionComment.objects.filter(
                pk=params['parent'], collection=collection, is_story=is_story
            ).first()
            if parent is None:
                raise ValidationError({'parent': ['That comment is not in this thread.']})
            # Replies are one level deep: a reply to a reply joins the same thread.
            if parent.parent_id:
                parent = parent.parent

        day = placement = None
        if not is_story:
            if params.get('day'):
                day = CollectionItineraryDay.objects.filter(pk=params['day'], collection=collection).first()
                if day is None:
                    raise ValidationError({'day': ['That day is not in this collection.']})
            if params.get('placement'):
                placement = CollectionItineraryItem.objects.filter(pk=params['placement'], collection=collection).first()
                if placement is None:
                    raise ValidationError({'placement': ['That item is not in this collection.']})
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
            thread=params['thread'],
            day_index=day.index if day else None,
            excerpt=body[:140],
        )
        page = request.build_absolute_uri(f'/collections/{collection.pk}') if mentioned else None
        transaction.on_commit(lambda: notify_mentions(comment, mentioned, page))
        return Response(serialize_comment(comment, request, story=is_story), status=status.HTTP_201_CREATED)


class CommentViewSet(mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """One comment, and the signed-in user's inbox of new comments."""

    openapi_tags = ['Comments']
    permission_classes = [AllowAny]
    queryset = CollectionComment.objects.all()
    http_method_names = ['get', 'patch', 'delete', 'post', 'head', 'options']

    def get_object(self):
        comment = (
            CollectionComment.objects.select_related('collection', 'author_user', 'day')
            .filter(pk=self.kwargs['pk'])
            .first()
            if as_uuid(self.kwargs.get('pk')) else None
        )
        if comment is None or not can_read_thread(self.request, comment.collection, comment.is_story):
            raise NotFound('Comment not found.')
        return comment

    @extend_schema(request=CommentUpdateSerializer, responses=CommentSerializer)
    def partial_update(self, request, pk=None):
        """
        Edit a comment

        Only its author can. Marks it edited.
        """
        comment = self.get_object()
        if not is_author(request, comment):
            raise PermissionDenied('You can only edit your own comments.')
        body = validated(CommentUpdateSerializer, request.data)['body'].strip()
        if not body:
            raise ValidationError({'body': ['Write something first.']})
        comment.body = body
        comment.edited_at = timezone.now()
        comment.save(update_fields=['body', 'edited_at'])
        if not comment.is_story:
            comment.mentions.set(resolve_mentions(comment.collection, comment.body))
        return Response(serialize_comment(comment, request, story=comment.is_story))

    @extend_schema(responses={204: OpenApiResponse(description='Deleted, with its replies.')})
    def destroy(self, request, pk=None):
        """
        Delete a comment

        Its author can, and so can the collection owner and editors (moderators).
        """
        comment = self.get_object()
        if not (is_author(request, comment) or can_moderate(request, comment)):
            raise PermissionDenied('You can only delete your own comments.')
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(parameters=[InboxQuerySerializer], responses=InboxSerializer)
    @action(detail=False, methods=['get'], url_path='inbox', permission_classes=[IsAuthenticated])
    def inbox(self, request):
        """
        Get your comment inbox

        New comments on the plans of collections you belong to and on the stories you own,
        newest first, without your own. `unread_count` counts those since you last marked
        the inbox seen.
        """
        params = validated(InboxQuerySerializer, request.query_params)
        user = request.user
        state = CommentInboxState.objects.filter(user=user).first()
        seen_at = state.seen_at if state else None
        qs = (
            inbox_queryset(user)
            .select_related('collection', 'author_user', 'day')
            .prefetch_related('mentions')
            .order_by('-created_at')
        )
        items = [
            {
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
            }
            for comment in qs[:params['limit']]
        ]
        unread = qs.filter(created_at__gt=seen_at).count() if seen_at else qs.count()
        return Response({'unread_count': unread, 'comments': items})

    @extend_schema(request=None, responses=UnreadCountSerializer)
    @action(detail=False, methods=['post'], url_path='inbox/mark-seen', permission_classes=[IsAuthenticated])
    def mark_inbox_seen(self, request):
        """Mark your inbox seen"""
        CommentInboxState.objects.update_or_create(user=request.user, defaults={'seen_at': timezone.now()})
        return Response({'unread_count': 0})


@extend_schema(parameters=[COLLECTION_ID_PARAMETER])
class CollectionActivityViewSet(CollectionScopedMixin, viewsets.ViewSet):
    openapi_tags = ['Comments']
    permission_classes = [AllowAny]

    @extend_schema(parameters=[ActivityFeedQuerySerializer], responses=ActivityEventSerializer(many=True))
    def list(self, request, collection_id=None):
        """
        Get the activity feed

        What changed in the collection and who did it, newest first. For the owner and
        editors; only the owner sees membership changes. Viewers get 403.
        """
        params = validated(ActivityFeedQuerySerializer, request.query_params)
        collection = self.get_collection()
        audience = audience_for_request(request, collection)
        if audience is None or not audience.is_member:
            raise NotFound('Collection not found.')
        if not audience.can_edit:
            raise PermissionDenied('Viewers do not see the activity feed.')
        events = visible_activity(collection, audience)[:params['limit']]
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

