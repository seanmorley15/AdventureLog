from rest_framework import viewsets
from django.db.models import Q
from adventures.models import Location, Activity
from adventures.serializers import ActivitySerializer
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from rest_framework.exceptions import PermissionDenied
import gpxpy
from typing import Tuple

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
        location = visit.location

        if location and not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, location):
            raise PermissionDenied("You do not have permission to add an activity to this location.")

        # if there is a GPX file, use it to get elevation data
        gpx_file = serializer.validated_data.get('gpx_file')
        if gpx_file:
            elevation_gain, elevation_loss, elevation_high, elevation_low = self._get_elevation_data_from_gpx(gpx_file)
            serializer.validated_data['elevation_gain'] = elevation_gain
            serializer.validated_data['elevation_loss'] = elevation_loss
            serializer.validated_data['elev_high'] = elevation_high
            serializer.validated_data['elev_low'] = elevation_low

        serializer.save(user=location.user)

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

    def _get_elevation_data_from_gpx(self, gpx_file) -> Tuple[float, float, float, float]:
        """
        Extract elevation data from a GPX file.
        Returns: (elevation_gain, elevation_loss, elevation_high, elevation_low)
        """
        try:
            # Parse the GPX file
            gpx_file.seek(0)  # Reset file pointer if needed
            gpx = gpxpy.parse(gpx_file)
            
            elevations = []
            
            # Extract all elevation points from tracks and track segments
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        if point.elevation is not None:
                            elevations.append(point.elevation)
            
            # Also check waypoints for elevation data
            for waypoint in gpx.waypoints:
                if waypoint.elevation is not None:
                    elevations.append(waypoint.elevation)
            
            # If no elevation data found, return zeros
            if not elevations:
                return 0.0, 0.0, 0.0, 0.0
            
            # Calculate basic stats
            elevation_high = max(elevations)
            elevation_low = min(elevations)
            
            # Calculate gain and loss by comparing consecutive points
            elevation_gain = 0.0
            elevation_loss = 0.0
            
            # Apply simple smoothing to reduce GPS noise (optional)
            smoothed_elevations = self._smooth_elevations(elevations)
            
            for i in range(1, len(smoothed_elevations)):
                diff = smoothed_elevations[i] - smoothed_elevations[i-1]
                if diff > 0:
                    elevation_gain += diff
                else:
                    elevation_loss += abs(diff)
            
            return elevation_gain, elevation_loss, elevation_high, elevation_low
            
        except Exception as e:
            # Log the error and return zeros
            print(f"Error parsing GPX file: {e}")
            return 0.0, 0.0, 0.0, 0.0

    def _smooth_elevations(self, elevations, window_size=3):
        """
        Apply simple moving average smoothing to reduce GPS elevation noise.
        """
        if len(elevations) < window_size:
            return elevations
        
        smoothed = []
        half_window = window_size // 2
        
        for i in range(len(elevations)):
            start = max(0, i - half_window)
            end = min(len(elevations), i + half_window + 1)
            smoothed.append(sum(elevations[start:end]) / (end - start))
        
        return smoothed