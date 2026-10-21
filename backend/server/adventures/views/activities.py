from django.db.models import Q
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view, inline_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from adventures.access.audience import can_edit, member_collections_q
from adventures.models import Activity, CollectionItineraryItem
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from adventures.serializers import ActivitySerializer, CollectionItineraryItemSerializer, VisitSerializer
from adventures.serializers.day_plan import DayDateField
from adventures.services.day_plan import DayPlanError
from adventures.services.day_plan.files import activity_collection, promote_day_activity
from adventures.services.gpx import fill_from_gpx
from adventures.services.media_quota import ensure_media_storage_available, get_uploaded_file_size
from core.exceptions import APIError
from core.serializers import validated


class ActivityLogVisitSerializer(serializers.Serializer):
    placement = serializers.UUIDField(
        required=False, allow_null=True,
        help_text='The location stop to log it on, when the day has more than one.',
    )
    date = DayDateField(required=False, allow_null=True, help_text='The visit date, for an undated trip.')


_QUOTA = OpenApiResponse(description="The GPX file would exceed the owner's media storage (`media_quota_exceeded`).")


@extend_schema_view(
    create=extend_schema(
        description='Attach it to a `visit`, a trip `day`, or a `collection` (its Ideas). Send `multipart/form-data` '
        'with a `gpx_file` to upload a track: elevation and start and end points missing from the request are read '
        'from it. A day or Ideas activity belongs to the collection owner.',
        responses={201: ActivitySerializer, 413: _QUOTA},
    ),
    update=extend_schema(responses={200: ActivitySerializer, 413: _QUOTA}),
    partial_update=extend_schema(
        description='The visit, day or collection cannot be changed.', responses={200: ActivitySerializer, 413: _QUOTA}
    ),
)
class ActivityViewSet(viewsets.ModelViewSet):
    """
    Activities: a hike, run, ride or other recorded outing, with distances, times and an optional GPX track.

    An activity is on a visit (of a location), on a trip day, or in a collection's Ideas.
    """

    openapi_tags = ['Activities']
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        """
        Returns activities based on location permissions.
        Users can only see activities in locations they have access to for editing/updating/deleting.
        This means they are either:
        - The owner of the location
        - The location is in a collection that is shared with the user
        - The location is in a collection that the user owns
        """
        if getattr(self, 'swagger_fake_view', False):
            return Activity.objects.none()
        user = self.request.user
        authenticated = bool(user and user.is_authenticated)

        # Day activities and Ideas activities, through the collection's members and guest links.
        day_filter = member_collections_q(self.request, 'day__collection__')
        day_filter |= member_collections_q(self.request, 'collection__')
        if not authenticated:
            return Activity.objects.filter(day_filter).distinct()

        # Place activities, through the visit's location.
        location_filter = Q(visit__location__user=user)
        location_filter |= Q(visit__location__collections__shared_with=user)
        location_filter |= Q(visit__location__collections__user=user)

        return Activity.objects.filter(location_filter | day_filter).distinct()

    def _storage_owner(self, visit, day, ideas):
        if day is not None:
            return day.collection.user
        if ideas is not None:
            return ideas.user
        return visit.location.user

    def _assert_parent_access(self, visit, day, ideas):
        if day is not None:
            if not can_edit(self.request, day.collection):
                raise PermissionDenied("You do not have permission to add an activity to this day.")
            return
        if ideas is not None:
            if not can_edit(self.request, ideas):
                raise PermissionDenied("You do not have permission to add an activity to this collection.")
            return
        if visit is None or visit.location is None:
            raise APIError('An activity belongs to a visit, a trip day, or Ideas.', code='invalid')
        if not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, visit.location):
            raise PermissionDenied("You do not have permission to add an activity to this location.")

    def perform_create(self, serializer):
        """
        Set the user when creating an activity.

        A day activity is owned by the collection owner and does not create a visit.
        """
        visit = serializer.validated_data.get('visit')
        day = serializer.validated_data.get('day')
        ideas = serializer.validated_data.get('collection')
        self._assert_parent_access(visit, day, ideas)
        owner = self._storage_owner(visit, day, ideas)

        gpx_file = serializer.validated_data.get('gpx_file')
        if gpx_file:
            ensure_media_storage_available(owner, get_uploaded_file_size(gpx_file))
            fill_from_gpx(serializer.validated_data, gpx_file)

        serializer.save(user=owner)

    def perform_update(self, serializer):
        instance = serializer.instance
        new_visit = serializer.validated_data.get('visit')
        new_day = serializer.validated_data.get('day')
        new_collection = serializer.validated_data.get('collection')
        new_gpx_file = serializer.validated_data.get('gpx_file')

        if new_visit and new_visit != instance.visit:
            raise PermissionDenied("Cannot change activity visit after creation. Create a new activity instead.")
        if new_day and new_day != instance.day:
            raise PermissionDenied("Cannot change activity day after creation. Create a new activity instead.")
        if new_collection and new_collection != instance.collection:
            raise PermissionDenied("Cannot change activity collection after creation. Create a new activity instead.")

        parent_collection = activity_collection(instance)
        location = instance.visit.location if instance.visit_id else None
        if parent_collection is not None:
            if not can_edit(self.request, parent_collection):
                raise PermissionDenied("You do not have permission to update this activity.")
            owner = parent_collection.user
        elif location is not None:
            if not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, location):
                raise PermissionDenied("You do not have permission to update this activity.")
            owner = location.user
        else:
            raise PermissionDenied("You do not have permission to update this activity.")

        if new_gpx_file:
            exclude_names = []
            if instance.gpx_file and instance.gpx_file.name:
                exclude_names.append(instance.gpx_file.name)
            ensure_media_storage_available(owner, get_uploaded_file_size(new_gpx_file), exclude_names=exclude_names)

        serializer.save()

    def perform_destroy(self, instance):
        parent_collection = activity_collection(instance)
        if parent_collection is not None:
            if not can_edit(self.request, parent_collection):
                raise PermissionDenied("You do not have permission to delete this activity.")
        else:
            location = instance.visit.location if instance.visit_id else None
            if location and not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, location):
                raise PermissionDenied("You do not have permission to delete this activity.")

        if instance.gpx_file:
            instance.gpx_file.delete(save=False)
        for image in instance.images.all():
            image.delete()
        instance.delete()

    @extend_schema(
        request=ActivityLogVisitSerializer,
        responses={
            201: OpenApiResponse(inline_serializer('ActivityLogVisitResult', fields={
                'activity': ActivitySerializer(),
                'visit': VisitSerializer(),
                'created': serializers.BooleanField(),
                'item': CollectionItineraryItemSerializer(required=False, help_text='The stop it was logged on.'),
            }), description='A visit was created.'),
            200: OpenApiResponse(description='Logged on an existing visit; same body.'),
            400: OpenApiResponse(description='`stop_required` (pick a `placement`), `date_required`, or invalid input.'),
        },
    )
    @action(detail=True, methods=['post'], url_path='log-visit')
    def log_visit(self, request, pk=None):
        """
        Log a day activity as a visit

        Copies a trip-day activity onto the visit of one location stop on that day (creating
        the visit when needed). The day activity stays on the day.
        """
        activity = self.get_object()
        if not can_edit(request, activity_collection(activity)):
            raise PermissionDenied("You do not have permission to log this activity.")
        params = validated(ActivityLogVisitSerializer, request.data)
        placement = None
        if params.get('placement'):
            placement = CollectionItineraryItem.objects.filter(pk=params['placement']).first()
            if placement is None:
                raise DayPlanError('That stop is not on this day.')
        visit, _copy, created = promote_day_activity(activity, placement=placement, visit_date=params.get('date'))
        activity.refresh_from_db()
        placement = activity.promoted_activity and CollectionItineraryItem.objects.filter(
            logged_visit=visit, object_id=visit.location_id
        ).select_related('day', 'content_type').order_by('-updated_at').first()
        body = {
            'activity': self.get_serializer(activity).data,
            'visit': VisitSerializer(visit, context=self.get_serializer_context()).data,
            'created': created,
        }
        if placement is not None:
            body['item'] = CollectionItineraryItemSerializer(placement, context=self.get_serializer_context()).data
        return Response(body, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
