from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.exceptions import NotAuthenticated, PermissionDenied

from adventures.models import Visit
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from adventures.serializers import VisitSerializer
from adventures.services.geocoding.assignment import geocode_and_assign_location


@extend_schema_view(
    list=extend_schema(description='Visits to locations you own or that are in collections you belong to.'),
    create=extend_schema(
        description='Send `location`. A visit in the past makes the location visited, which also marks its '
        'region and city visited.'
    ),
    partial_update=extend_schema(description='The location of a visit cannot be changed.'),
)
class VisitViewSet(viewsets.ModelViewSet):
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
        
        return Visit.objects.filter(location_filter).distinct()

    def perform_create(self, serializer):
        """
        Set the user when creating a visit and check permissions.
        """
        location = serializer.validated_data.get('location')

        if not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, location):
            raise PermissionDenied("You do not have permission to add a visit to this location.")

        serializer.save()

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

        serializer.save()

        geocode_and_assign_location(str(instance.location.id))

    def perform_destroy(self, instance):
        if not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, instance.location):
            raise PermissionDenied("You do not have permission to delete this visit.")

        instance.delete()