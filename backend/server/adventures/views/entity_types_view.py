from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from adventures.models import TransportationType, LodgingType, AdventureType, ActivityType
from adventures.serializers import TransportationTypeSerializer, LodgingTypeSerializer, AdventureTypeSerializer, ActivityTypeSerializer


class TransportationTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for transportation types.
    Read-only - types are managed via Django admin.
    """
    queryset = TransportationType.objects.filter(is_active=True)
    serializer_class = TransportationTypeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Return all types without pagination


class LodgingTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for lodging types.
    Read-only - types are managed via Django admin.
    """
    queryset = LodgingType.objects.filter(is_active=True)
    serializer_class = LodgingTypeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Return all types without pagination


class AdventureTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for adventure types (location categories).
    Read-only - types are managed via Django admin.
    """
    queryset = AdventureType.objects.filter(is_active=True)
    serializer_class = AdventureTypeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Return all types without pagination


class ActivityTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for activity/sport types.
    Read-only - types are managed via Django admin.
    """
    queryset = ActivityType.objects.filter(is_active=True)
    serializer_class = ActivityTypeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Return all types without pagination
