from rest_framework import viewsets
from django.db.models import Q
from adventures.models import Location, Activity
from adventures.serializers import ActivitySerializer
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from rest_framework.exceptions import PermissionDenied

class ActivityViewSet(viewsets.ModelViewSet):
    serializer_class = ActivitySerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess]

    def get_queryset(self):
        """
        Returns activities based on location permissions.
        Users can only see activities in locations they have access to for editing/updating/deleting.
        This means they are either:
        - The owner of the location
        - The location is in a collection that is shared with the user
        - The location is in a collection that the user owns
        """
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return Activity.objects.none()
        
        # Build the filter for accessible locations
        location_filter = Q(visit__location__user=user)  # User owns the location
        
        # Location is in collections (many-to-many) that are shared with user
        location_filter |= Q(visit__location__collections__shared_with=user)
        
        # Location is in collections (many-to-many) that user owns
        location_filter |= Q(visit__location__collections__user=user)
        
        return Activity.objects.filter(location_filter).distinct()

    def perform_create(self, serializer):
        """
        Set the user when creating an activity.
        """
        visit = serializer.validated_data.get('visit')
        location = visit.location if visit else None

        if location and not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, location):
            raise PermissionDenied("You do not have permission to add an activity to this location.")

        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.instance
        new_visit = serializer.validated_data.get('visit')
        
        # Prevent changing visit/location after creation
        if new_visit and new_visit != instance.visit:
            raise PermissionDenied("Cannot change activity visit after creation. Create a new activity instead.")
        
        # Check permission for updates to the existing location
        location = instance.visit.location if instance.visit else None
        if location and not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, location):
            raise PermissionDenied("You do not have permission to update this activity.")

        serializer.save()

    def perform_destroy(self, instance):
        location = instance.visit.location if instance.visit else None
        if location and not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, location):
            raise PermissionDenied("You do not have permission to delete this activity.")

        instance.delete()