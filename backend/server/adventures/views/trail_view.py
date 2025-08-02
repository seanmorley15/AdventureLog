from rest_framework import viewsets
from django.db.models import Q
from adventures.models import Location, Trail
from adventures.serializers import TrailSerializer
from adventures.permissions import IsOwnerOrSharedWithFullAccess

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
            return Trail.objects.none()
        
        # Build the filter for accessible locations
        location_filter = Q(location__user=user)  # User owns the location
        
        # Location is in collections (many-to-many) that are shared with user
        location_filter |= Q(location__collections__shared_with=user)
        
        # Location is in collections (many-to-many) that user owns
        location_filter |= Q(location__collections__user=user)
        
        return Trail.objects.filter(location_filter).distinct()

    def perform_create(self, serializer):
        """
        Set the user when creating a trail.
        """
        serializer.save(user=self.request.user)