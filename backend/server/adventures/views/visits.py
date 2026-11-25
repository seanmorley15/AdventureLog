from django.db import transaction
from django.db.models import Q
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from adventures.models import Visit
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from adventures.serializers import VisitSerializer
from adventures.services import travelers
from adventures.services.geocoding.assignment import geocode_and_assign_location
from core.serializers import validated
from core.sync import ClientIdsMixin, ConditionalWritesMixin


class VisitDeleteQuerySerializer(serializers.Serializer):
    for_everyone = serializers.BooleanField(
        default=False,
        help_text='Delete the visit for every traveler. Only the location owner may. Otherwise only you are '
        'removed from it.',
    )


@extend_schema_view(
    destroy=extend_schema(
        description='A traveler is removed from the visit, which is deleted when they were its last traveler. '
        'The location owner deletes it for everyone with `for_everyone`, and without it deletes a visit nobody '
        'travelled on. 204 when something changed. The location owner not on a visit others travelled on gets '
        '409 `visit_has_travelers`; anyone else not on it gets 403 `not_a_traveler`.',
        parameters=[VisitDeleteQuerySerializer],
        responses={
            204: OpenApiResponse(description='You were removed, or the visit was deleted.'),
            409: OpenApiResponse(description='`visit_has_travelers`: others travelled on it; use `for_everyone`.'),
        },
    ),
    list=extend_schema(description='Visits to locations you own or that are in collections you belong to.'),
    create=extend_schema(
        description='Send `location`. A visit in the past makes the location visited, which also marks its '
        'region and city visited.'
    ),
    partial_update=extend_schema(description='The location of a visit cannot be changed.'),
)
class VisitViewSet(ConditionalWritesMixin, ClientIdsMixin, viewsets.ModelViewSet):
    """
    Visits: the dates you were at a location, with notes and a time zone.

    Owners and editors of a collection the location is in can add and change its visits.
    """

    openapi_tags = ['Visits']
    queryset = Visit.objects.all()
    serializer_class = VisitSerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess]

    def get_queryset(self):
        """
        Returns visits based on location permissions.
        Users can only see visits in locations they have access to for editing/updating/deleting.
        This means they are either:
        - The owner of the location
        - The location is in a collection that is shared with the user
        - The location is in a collection that the user owns
        - The user is a traveler on the visit (so they can leave it after leaving the trip)
        """
        if getattr(self, 'swagger_fake_view', False):
            return Visit.objects.none()
        user = self.request.user
        if not user or not user.is_authenticated:
            raise NotAuthenticated()
        
        # Build the filter for accessible locations
        location_filter = Q(location__user=user)  # User owns the location
        
        # Location is in collections (many-to-many) that are shared with user
        location_filter |= Q(location__collections__shared_with=user)
        
        # Location is in collections (many-to-many) that user owns
        location_filter |= Q(location__collections__user=user)

        # The user travelled on the visit
        location_filter |= Q(travelers=user)
        
        return Visit.objects.filter(location_filter).distinct()

    def perform_create(self, serializer):
        """
        Set the user when creating a visit and check permissions.
        """
        location = serializer.validated_data.get('location')

        if not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, location):
            raise PermissionDenied("You do not have permission to add a visit to this location.")

        # A visit nobody can be named on is refused whole: nothing is saved.
        with transaction.atomic():
            visit = serializer.save()
            people = serializer.validated_data.get('traveler_uuids')
            travelers.set_travelers(
                visit, people if people is not None else [self.request.user], self.request.user, fresh=True
            )

        # This will update any visited regions or cities based on if it's now visited
        geocode_and_assign_location(str(location.id))

    def perform_update(self, serializer):
        instance = serializer.instance
        new_location = serializer.validated_data.get('location')
        
        # Prevent changing location after creation
        if new_location and new_location != instance.location:
            raise PermissionDenied("Cannot change visit location after creation. Create a new visit instead.")

        # Check permission for updates to the existing location
        if not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, instance.location):
            raise PermissionDenied("You do not have permission to update this visit.")

        with transaction.atomic():
            visit = serializer.save()
            people = serializer.validated_data.get('traveler_uuids')
            if people is not None:
                travelers.set_travelers(visit, people, self.request.user)

        geocode_and_assign_location(str(instance.location.id))

    def perform_destroy(self, instance):
        if not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, instance.location):
            raise PermissionDenied("You do not have permission to delete this visit.")

        params = validated(VisitDeleteQuerySerializer, self.request.query_params)
        travelers.remove_or_delete(instance, self.request.user, params['for_everyone'])

    @extend_schema(
        request=None,
        responses={200: VisitSerializer, 403: OpenApiResponse(description='You cannot join this visit.')},
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def join(self, request, pk=None):
        """
        Join a visit

        Adds you as a traveler. Any member of a collection holding the location may join,
        viewers included. People who cannot see the visit get a 404.
        """
        visit = self.get_object()
        travelers.join(visit, request.user)
        return Response(self.get_serializer(visit).data)

    @extend_schema(
        request=None,
        responses={
            200: VisitSerializer,
            204: OpenApiResponse(description='You were the last traveler, so the visit was deleted.'),
        },
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def leave(self, request, pk=None):
        """
        Leave a visit

        Removes you as a traveler. When nobody is left the visit is deleted.
        """
        visit = self.get_object()
        if travelers.leave(visit, request.user):
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(self.get_serializer(visit).data)
