from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.conf import settings
from adventures.models import Lodging, LODGING_TYPES
from adventures.serializers import LodgingSerializer, LodgingMapPinSerializer
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from adventures.utils import pagination
from adventures.utils.filtering import FilteringMixin
from adventures.utils.viewset_mixins import ViewsetUtilsMixin
from adventures.utils.history_mixin import HistoryRevertMixin
from adventures.utils.collaborative_mixin import (
    CollaborativeQuerySetMixin, EntityCRUDMixin, SunTimesMixin, TypeFilteredMixin
)

class LodgingViewSet(
    HistoryRevertMixin,
    CollaborativeQuerySetMixin,
    EntityCRUDMixin,
    SunTimesMixin,
    TypeFilteredMixin,
    FilteringMixin,
    ViewsetUtilsMixin,
    viewsets.ModelViewSet
):
    """
    ViewSet for managing Lodging objects.

    Inherits filtering and sorting from mixins:
    - FilteringMixin: _apply_visit_filtering, _apply_public_filtering,
                      _apply_ownership_filtering, _apply_rating_filtering
    - ViewsetUtilsMixin: apply_sorting, paginate_and_respond
    - HistoryRevertMixin: history, revert
    - CollaborativeQuerySetMixin: get_queryset, list
    - EntityCRUDMixin: partial_update, perform_create, perform_update
    - SunTimesMixin: additional_info, _get_sun_times
    - TypeFilteredMixin: filtered
    """
    queryset = Lodging.objects.all()
    serializer_class = LodgingSerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess]
    pagination_class = pagination.StandardResultsSetPagination

    # Override valid_order_fields from SortingMixin
    valid_order_fields = ['name', 'last_visit', 'rating', 'updated_at', 'created_at']

    # SunTimesMixin config (uses standard latitude/longitude)
    lat_field = 'latitude'
    lng_field = 'longitude'

    # TypeFilteredMixin config
    type_choices = LODGING_TYPES
    entity_type_label = 'lodging'

    # ==================== SORTING ====================

    def apply_sorting(self, queryset):
        """
        Apply sorting and collection filtering to queryset.
        Extends SortingMixin.apply_sorting with include_collections filter.
        """
        queryset = super().apply_sorting(queryset)

        include_collections = self.request.query_params.get('include_collections', 'true')
        if include_collections == 'false':
            queryset = queryset.filter(collections__isnull=True)

        return queryset

    # ==================== CUSTOM ACTIONS ====================

    @action(detail=False, methods=['get'], url_path='pins')
    def pins(self, request):
        """Get all lodging with coordinates for map display."""
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)

        is_collaborative = getattr(settings, 'COLLABORATIVE_MODE', False)

        if is_collaborative:
            base_filter = Q(user=request.user) | Q(is_public=True) | Q(collections__shared_with=request.user)
        else:
            base_filter = Q(user=request.user) | Q(collections__shared_with=request.user)

        # Only get lodging with coordinates
        lodgings = Lodging.objects.filter(
            base_filter,
            latitude__isnull=False,
            longitude__isnull=False
        ).distinct()

        serializer = LodgingMapPinSerializer(lodgings, many=True, context={'request': request})
        return Response(serializer.data)
