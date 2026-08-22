from rest_framework import viewsets
from django.db.models import Q
from adventures.models import Location, Activity
from adventures.serializers import ActivitySerializer
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from rest_framework.exceptions import PermissionDenied, ValidationError
import gpxpy
from typing import Tuple
from users.media_utils import enforce_media_storage_limit, get_uploaded_file_size

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

        # if there is a GPX file, fill missing elevation / start-end coords from it
        gpx_file = serializer.validated_data.get('gpx_file')
        if gpx_file:
            allowed, details = enforce_media_storage_limit(
                location.user,
                get_uploaded_file_size(gpx_file),
            )
            if not allowed:
                raise ValidationError({
                    "error": "Media storage limit exceeded",
                    **details,
                })
            elevation_gain, elevation_loss, elevation_high, elevation_low = self._get_elevation_data_from_gpx(gpx_file)
            # Prefer explicitly provided values (e.g. Endurain/Strava totals) over GPX-derived ones.
            # When GPX has no elevation samples, _get_elevation_data_from_gpx returns None.
            if serializer.validated_data.get('elevation_gain') is None and elevation_gain is not None:
                serializer.validated_data['elevation_gain'] = elevation_gain
            if serializer.validated_data.get('elevation_loss') is None and elevation_loss is not None:
                serializer.validated_data['elevation_loss'] = elevation_loss
            if serializer.validated_data.get('elev_high') is None and elevation_high is not None:
                serializer.validated_data['elev_high'] = elevation_high
            if serializer.validated_data.get('elev_low') is None and elevation_low is not None:
                serializer.validated_data['elev_low'] = elevation_low

            start_lat, start_lng, end_lat, end_lng = self._get_start_end_from_gpx(gpx_file)
            if serializer.validated_data.get('start_lat') is None and start_lat is not None:
                serializer.validated_data['start_lat'] = start_lat
            if serializer.validated_data.get('start_lng') is None and start_lng is not None:
                serializer.validated_data['start_lng'] = start_lng
            if serializer.validated_data.get('end_lat') is None and end_lat is not None:
                serializer.validated_data['end_lat'] = end_lat
            if serializer.validated_data.get('end_lng') is None and end_lng is not None:
                serializer.validated_data['end_lng'] = end_lng

        serializer.save(user=location.user)

    def perform_update(self, serializer):
        instance = serializer.instance
        new_visit = serializer.validated_data.get('visit')
        new_gpx_file = serializer.validated_data.get('gpx_file')
        
        # Prevent changing visit/location after creation
        if new_visit and new_visit != instance.visit:
            raise PermissionDenied("Cannot change activity visit after creation. Create a new activity instead.")
        
        # Check permission for updates to the existing location
        location = instance.visit.location if instance.visit else None
        if location and not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, location):
            raise PermissionDenied("You do not have permission to update this activity.")

        if new_gpx_file and location:
            exclude_names = []
            if instance.gpx_file and instance.gpx_file.name:
                exclude_names.append(instance.gpx_file.name)
            allowed, details = enforce_media_storage_limit(
                location.user,
                get_uploaded_file_size(new_gpx_file),
                exclude_names=exclude_names,
            )
            if not allowed:
                raise ValidationError({
                    "error": "Media storage limit exceeded",
                    **details,
                })

        serializer.save()

    def perform_destroy(self, instance):
        location = instance.visit.location if instance.visit else None
        if location and not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, location):
            raise PermissionDenied("You do not have permission to delete this activity.")

        instance.delete()

    def _get_elevation_data_from_gpx(self, gpx_file) -> Tuple[float | None, float | None, float | None, float | None]:
        """
        Extract elevation data from a GPX file.
        Returns: (elevation_gain, elevation_loss, elevation_high, elevation_low)
        Returns (None, None, None, None) when the GPX has no elevation samples.
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
            
            # If no elevation data found, leave existing values alone
            if not elevations:
                return None, None, None, None
            
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
            # Log the error and leave existing values alone
            print(f"Error parsing GPX file: {e}")
            return None, None, None, None

    def _get_start_end_from_gpx(self, gpx_file) -> Tuple[float | None, float | None, float | None, float | None]:
        """
        Extract start/end coordinates from a GPX track.
        Returns: (start_lat, start_lng, end_lat, end_lng)
        """
        try:
            gpx_file.seek(0)
            gpx = gpxpy.parse(gpx_file)
            points = []
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        if point.latitude is not None and point.longitude is not None:
                            points.append((point.latitude, point.longitude))
            if not points:
                return None, None, None, None
            start_lat, start_lng = points[0]
            end_lat, end_lng = points[-1]
            return start_lat, start_lng, end_lat, end_lng
        except Exception as e:
            print(f"Error extracting GPX coordinates: {e}")
            return None, None, None, None

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