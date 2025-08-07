from rest_framework import viewsets
from django.db.models import Q
from adventures.models import Location, Trail
from adventures.serializers import TrailSerializer
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from rest_framework.exceptions import PermissionDenied

class TrailViewSet(viewsets.ModelViewSet):
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
        user = self.request.user
        
        if not user or not user.is_authenticated:
            raise PermissionDenied("You must be authenticated to view trails.")

        # Build the filter for accessible locations
        location_filter = Q(location__user=user)  # User owns the location
        
        # Location is in collections (many-to-many) that are shared with user
        location_filter |= Q(location__collections__shared_with=user)
        
        # Location is in collections (many-to-many) that user owns
        location_filter |= Q(location__collections__user=user)
        
        return Trail.objects.filter(location_filter).distinct()

    def perform_create(self, serializer):
        location = serializer.validated_data.get('location')

        if not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, location):
            raise PermissionDenied("You do not have permission to add a trail to this location.")

        # dont allow a user who does not own the location to attach a wanderer trail
        if location.user != self.request.user and serializer.validated_data.get('wanderer_id'):
            raise PermissionDenied("You cannot attach a wanderer trail to a location you do not own.")

        serializer.save(user=location.user)

    def perform_update(self, serializer):
        instance = serializer.instance
        new_location = serializer.validated_data.get('location')
        
        # Prevent changing location after creation
        if new_location and new_location != instance.location:
            raise PermissionDenied("Cannot change trail location after creation. Create a new trail instead.")
        
        # Check permission for updates to the existing location
        if not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, instance.location):
            raise PermissionDenied("You do not have permission to update this trail.")

        serializer.save()

    def perform_destroy(self, instance):
        if not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, instance.location):
            raise PermissionDenied("You do not have permission to delete this trail.")

        instance.delete()