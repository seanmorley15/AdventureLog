from rest_framework import viewsets
from django.db.models import Q
from adventures.models import Location, Visit
from adventures.serializers import VisitSerializer
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from rest_framework.exceptions import PermissionDenied
from adventures.models import background_geocode_and_assign

class VisitViewSet(viewsets.ModelViewSet):
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
        user = self.request.user
        
        if not user or not user.is_authenticated:
            raise PermissionDenied("You must be authenticated to view visits.")
        
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
        background_geocode_and_assign(str(location.id))

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

        background_geocode_and_assign(str(instance.location.id))

    def perform_destroy(self, instance):
        if not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, instance.location):
            raise PermissionDenied("You do not have permission to delete this visit.")

        instance.delete()