"""Your notifications. Rules live in services/notifications.py."""
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from adventures.models import Notification
from adventures.serializers.discussion import UnreadCountSerializer
from adventures.serializers.notification import (
    MarkNotificationsReadSerializer,
    NotificationQuerySerializer,
    NotificationSerializer,
)
from adventures.services.notifications import mark_read, serialize_notification, unread_notification_count
from core.pagination import StandardResultsSetPagination
from core.serializers import validated


class NotificationPagination(StandardResultsSetPagination):
    """The usual page, plus how many notifications are unread in all."""

    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        response.data['unread_count'] = self.unread_count
        return response

    def get_paginated_response_schema(self, schema):
        schema = super().get_paginated_response_schema(schema)
        schema['properties']['unread_count'] = {'type': 'integer', 'example': 2}
        schema['required'] = [*schema.get('required', []), 'unread_count']
        return schema


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Your notifications, such as being added to a visit. Only you can read or mark them.
    """

    openapi_tags = ['Notifications']
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    pagination_class = NotificationPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user).select_related('actor_user')

    @extend_schema(parameters=[NotificationQuerySerializer], responses=NotificationSerializer(many=True))
    def list(self, request, *args, **kwargs):
        """
        List your notifications

        Newest first. `unread_count` counts all your unread notifications, whatever the page or filter.
        `?unread=1` leaves out the ones you have read.
        """
        params = validated(NotificationQuerySerializer, request.query_params)
        queryset = self.get_queryset()
        if params['unread']:
            queryset = queryset.filter(read_at__isnull=True)
        paginator = self.paginator
        paginator.unread_count = unread_notification_count(request.user)
        page = paginator.paginate_queryset(queryset, request, view=self)
        data = [serialize_notification(note, request.user) for note in page]
        return paginator.get_paginated_response(data)

    @extend_schema(request=MarkNotificationsReadSerializer, responses=UnreadCountSerializer)
    @action(detail=False, methods=['post'], url_path='mark-read')
    def mark_read(self, request):
        """
        Mark notifications read

        Send `ids` to mark those, or nothing to mark all of yours. Ids that are not yours are ignored.
        Answers with how many are still unread.
        """
        data = validated(MarkNotificationsReadSerializer, request.data)
        return Response({'unread_count': mark_read(request.user, data.get('ids'))})
