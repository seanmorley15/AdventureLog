from rest_framework import viewsets
from django.db.models import Q
from django.conf import settings
from adventures.models import Location, Visit, Transportation, Lodging
from adventures.serializers import VisitSerializer
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from rest_framework.exceptions import PermissionDenied
from adventures.utils.geocoding_tasks import background_geocode

class VisitViewSet(viewsets.ModelViewSet):
    serializer_class = VisitSerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess]

    def get_queryset(self):
        """
        Returns visits based on parent object permissions.
        Users can only see visits for objects they have access to for editing/updating/deleting.
        This means they are either:
        - The owner of the location/transportation/lodging
        - The location is in a collection that is shared with the user
        - The location is in a collection that the user owns
        - The transportation/lodging is in a collection that is shared with the user
        - The transportation/lodging is in a collection that the user owns
        - In collaborative mode: the location/transportation/lodging is public
        """
        user = self.request.user

        if not user or not user.is_authenticated:
            raise PermissionDenied("You must be authenticated to view visits.")

        # Build the filter for accessible locations
        location_filter = Q(location__user=user)  # User owns the location
        location_filter |= Q(location__collections__shared_with=user)
        location_filter |= Q(location__collections__user=user)

        # Build the filter for accessible transportations
        transportation_filter = Q(transportation__user=user)  # User owns the transportation
        transportation_filter |= Q(transportation__collections__shared_with=user)
        transportation_filter |= Q(transportation__collections__user=user)

        # Build the filter for accessible lodgings
        lodging_filter = Q(lodging__user=user)  # User owns the lodging
        lodging_filter |= Q(lodging__collections__shared_with=user)
        lodging_filter |= Q(lodging__collections__user=user)

        # In collaborative mode, include visits from public items
        if getattr(settings, 'COLLABORATIVE_MODE', False):
            location_filter |= Q(location__is_public=True)
            transportation_filter |= Q(transportation__is_public=True)
            lodging_filter |= Q(lodging__is_public=True)

        # Combine all filters - a visit can be for location, transportation, or lodging
        combined_filter = location_filter | transportation_filter | lodging_filter

        return Visit.objects.filter(combined_filter).distinct()

    def perform_create(self, serializer):
        """
        Set the user when creating a visit and check permissions.
        A visit can be for a Location, Transportation, or Lodging.
        """
        location = serializer.validated_data.get('location')
        transportation = serializer.validated_data.get('transportation')
        lodging = serializer.validated_data.get('lodging')

        # Determine which parent object this visit is for
        parent_object = location or transportation or lodging

        if not parent_object:
            raise PermissionDenied("A visit must be associated with a location, transportation, or lodging.")

        if not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, parent_object):
            raise PermissionDenied("You do not have permission to add a visit to this item.")

        serializer.save()

        # This will update any visited regions or cities based on if it's now visited (only for locations)
        if location:
            background_geocode(Location, str(location.id))

    def perform_update(self, serializer):
        instance = serializer.instance
        new_location = serializer.validated_data.get('location')
        new_transportation = serializer.validated_data.get('transportation')
        new_lodging = serializer.validated_data.get('lodging')

        # Prevent changing parent object after creation
        if new_location and instance.location and new_location != instance.location:
            raise PermissionDenied("Cannot change visit location after creation. Create a new visit instead.")
        if new_transportation and instance.transportation and new_transportation != instance.transportation:
            raise PermissionDenied("Cannot change visit transportation after creation. Create a new visit instead.")
        if new_lodging and instance.lodging and new_lodging != instance.lodging:
            raise PermissionDenied("Cannot change visit lodging after creation. Create a new visit instead.")

        # In collaborative mode, users can only edit their own visits
        if getattr(settings, 'COLLABORATIVE_MODE', False):
            if instance.user and instance.user != self.request.user:
                raise PermissionDenied("You can only edit your own visits.")

        # Check permission for updates to the existing parent object
        parent_object = instance.location or instance.transportation or instance.lodging
        if not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, parent_object):
            raise PermissionDenied("You do not have permission to update this visit.")

        serializer.save()

        # Update geocoding for locations only
        if instance.location:
            background_geocode(Location, str(instance.location.id))

    def perform_destroy(self, instance):
        # In collaborative mode, users can only delete their own visits
        if getattr(settings, 'COLLABORATIVE_MODE', False):
            if instance.user and instance.user != self.request.user:
                raise PermissionDenied("You can only delete your own visits.")

        # Check permission for the parent object
        parent_object = instance.location or instance.transportation or instance.lodging
        if not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, parent_object):
            raise PermissionDenied("You do not have permission to delete this visit.")

        instance.delete()