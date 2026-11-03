from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.exceptions import NotAuthenticated, PermissionDenied, ValidationError

from adventures.access.audience import can_edit, has_guest_token, member_collections_q
from adventures.models import Trail
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from adventures.serializers import TrailSerializer
from adventures.services import day_plan
from adventures.services.day_plan.files import trail_collection
from core.exceptions import APIError


@extend_schema_view(
    create=extend_schema(
        description='Attach it to a `location`, a trip `day` (optionally spanning to `span_end_index`), or a '
        '`collection` (its Ideas). Give a `link`, or a `wanderer_id` to show a trail from your Wanderer server; only '
        "the record's owner can attach a Wanderer trail."
    ),
    partial_update=extend_schema(description='The location, day or collection cannot be changed.'),
)
class TrailViewSet(viewsets.ModelViewSet):
    """Trails: a link to a route, or a trail from a Wanderer server, on a location, a trip day or Ideas."""

    openapi_tags = ['Trails']
    queryset = Trail.objects.all()
    serializer_class = TrailSerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess]

    def get_queryset(self):
        """
        Returns trails based on location permissions.
        Users can only see trails in locations they have access to for editing/updating/deleting.
        This means they are either:
        - The owner of the location
        - The location is in a collection that is shared with the user
        - The location is in a collection that the user owns
        """
        if getattr(self, 'swagger_fake_view', False):
            return Trail.objects.none()
        user = self.request.user
        authenticated = bool(user and user.is_authenticated)

        day_filter = member_collections_q(self.request, 'day__collection__')
        day_filter |= member_collections_q(self.request, 'collection__')
        if not authenticated:
            if not has_guest_token(self.request):
                raise NotAuthenticated()
            return Trail.objects.filter(day_filter).distinct()

        location_filter = Q(location__user=user)
        location_filter |= Q(location__collections__shared_with=user)
        location_filter |= Q(location__collections__user=user)

        return Trail.objects.filter(location_filter | day_filter).distinct()

    def _owner_collection(self, location, day, ideas):
        if day is not None:
            return day.collection
        if ideas is not None:
            return ideas
        return None

    def perform_create(self, serializer):
        location = serializer.validated_data.get('location')
        day = serializer.validated_data.get('day')
        ideas = serializer.validated_data.get('collection')
        parent = self._owner_collection(location, day, ideas)
        if parent is not None:
            if not can_edit(self.request, parent):
                raise PermissionDenied("You do not have permission to add a trail to this day.")
            owner = parent.user
            span = serializer.validated_data.get('span_end_index')
            if day is not None and span is not None:
                count = day_plan.day_count(day.collection)
                if span > count:
                    raise ValidationError({'span_end_index': 'That day is outside this trip.'})
        else:
            if location is None or not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, location):
                raise PermissionDenied("You do not have permission to add a trail to this location.")
            owner = location.user

        # Wanderer trails stay with the record owner. A collaborator can still add a link.
        if owner != self.request.user and serializer.validated_data.get('wanderer_id'):
            raise PermissionDenied("You cannot attach a wanderer trail to a record you do not own.")

        serializer.save(user=owner)

    def perform_update(self, serializer):
        instance = serializer.instance
        new_location = serializer.validated_data.get('location')
        new_day = serializer.validated_data.get('day')
        new_collection = serializer.validated_data.get('collection')

        if new_location and new_location != instance.location:
            raise APIError('A trail cannot move to another location. Create a new trail instead.', code='invalid')
        if new_day and new_day != instance.day:
            raise APIError('A trail cannot move to another day. Create a new trail instead.', code='invalid')
        if new_collection and new_collection != instance.collection:
            raise APIError('A trail cannot move to another collection. Create a new trail instead.', code='invalid')

        parent = trail_collection(instance)
        if parent is not None:
            if not can_edit(self.request, parent):
                raise PermissionDenied("You do not have permission to update this trail.")
            span = serializer.validated_data.get('span_end_index', instance.span_end_index)
            if instance.day_id and span is not None and span > day_plan.day_count(parent):
                raise ValidationError({'span_end_index': 'That day is outside this trip.'})
        elif not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, instance.location):
            raise PermissionDenied("You do not have permission to update this trail.")

        serializer.save()

    def perform_destroy(self, instance):
        parent = trail_collection(instance)
        if parent is not None:
            if not can_edit(self.request, parent):
                raise PermissionDenied("You do not have permission to delete this trail.")
        elif not instance.location_id or not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, instance.location):
            raise PermissionDenied("You do not have permission to delete this trail.")

        for image in instance.images.all():
            image.delete()
        instance.delete()