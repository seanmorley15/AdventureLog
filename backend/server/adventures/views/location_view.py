import logging
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Prefetch
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
import requests
from adventures.models import Location, Category, CollectionItineraryItem, Visit

logger = logging.getLogger(__name__)
from django.contrib.contenttypes.models import ContentType
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from adventures.serializers import LocationSerializer, MapPinSerializer, CalendarLocationSerializer
from adventures.utils import pagination
from adventures.utils.filtering import FilteringMixin
from adventures.utils.viewset_mixins import SortingMixin
from adventures.utils.history_mixin import HistoryRevertMixin

class LocationViewSet(HistoryRevertMixin, FilteringMixin, SortingMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing Adventure objects with support for filtering, sorting,
    and sharing functionality.

    Inherits filtering and sorting from mixins:
    - FilteringMixin: _apply_visit_filtering, _apply_public_filtering,
                      _apply_ownership_filtering, _apply_rating_filtering
    - SortingMixin: _apply_ordering (apply_sorting is overridden for location-specific logic)
    """
    serializer_class = LocationSerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess]
    pagination_class = pagination.StandardResultsSetPagination

    # Override valid_order_fields from SortingMixin
    valid_order_fields = ['name', 'type', 'last_visit', 'rating', 'updated_at', 'created_at']

    # ==================== QUERYSET & PERMISSIONS ====================

    def get_queryset(self):
        """
        Returns queryset based on user authentication and action type.
        Public actions allow unauthenticated access to public locations.
        In collaborative mode, authenticated users can access public locations for editing.
        """
        user = self.request.user
        public_allowed_actions = {'retrieve', 'additional_info'}
        is_collaborative = getattr(settings, 'COLLABORATIVE_MODE', False)

        if not user.is_authenticated:
            if self.action in public_allowed_actions:
                return Location.objects.retrieve_locations(
                    user, include_public=True
                ).order_by('-updated_at')
            return Location.objects.none()

        # In collaborative mode, include public locations for all actions (except destroy)
        # The permission class will handle fine-grained access control
        if is_collaborative and self.action != 'destroy':
            include_public = True
        else:
            include_public = self.action in public_allowed_actions

        return Location.objects.retrieve_locations(
            user,
            include_public=include_public,
            include_owned=True,
            include_shared=True
        ).order_by('-updated_at')

    # ==================== SORTING & FILTERING ====================

    def apply_sorting(self, queryset):
        """
        Apply sorting and collection filtering to queryset.

        Extends SortingMixin.apply_sorting with location-specific
        include_collections filter.
        """
        # Use parent sorting logic from SortingMixin
        queryset = super().apply_sorting(queryset)

        # Location-specific: filter by collection membership
        include_collections = self.request.query_params.get('include_collections', 'true')
        if include_collections == 'false':
            queryset = queryset.filter(collections__isnull=True)

        return queryset

    # ==================== CRUD OPERATIONS ====================

    @transaction.atomic
    def perform_create(self, serializer):
        """Create adventure with collection validation and ownership logic."""
        collections = serializer.validated_data.get('collections', [])

        # Validate permissions for all collections
        self._validate_collection_permissions(collections)

        # Determine what user to assign as owner
        user_to_assign = self.request.user
        
        if collections:
            # Use the current user as owner since ManyToMany allows multiple collection owners
            user_to_assign = self.request.user

        serializer.save(user=user_to_assign)

    def perform_update(self, serializer):
        """Update adventure."""
        # Just save the adventure - the signal will handle publicity updates
        serializer.save()

    def update(self, request, *args, **kwargs):
        """Handle adventure updates with collection permission validation."""
        instance = self.get_object()
        partial = kwargs.pop('partial', False)

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # Validate collection permissions if collections are being updated
        if 'collections' in serializer.validated_data:
            self._validate_collection_update_permissions(
                instance, serializer.validated_data['collections']
            )
        else:
            # Remove collections from validated_data if not provided
            serializer.validated_data.pop('collections', None)

        self.perform_update(serializer)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Only allow the owner to delete a location."""
        instance = self.get_object()
        
        # Check if the user is the owner
        if instance.user != request.user:
            raise PermissionDenied("Only the owner can delete this location.")
        
        return super().destroy(request, *args, **kwargs)

    # ==================== CUSTOM ACTIONS ====================

    @action(detail=False, methods=['get'], url_path='debug-collab')
    def debug_collab(self, request):
        """Debug endpoint to check collaborative mode status."""
        is_collaborative = getattr(settings, 'COLLABORATIVE_MODE', False)
        user_locations = Location.objects.filter(user=request.user).count()
        public_locations = Location.objects.filter(is_public=True).count()
        all_locations = Location.objects.retrieve_locations(
            request.user,
            include_owned=True,
            include_shared=True,
            include_public=is_collaborative
        ).count()
        return Response({
            "collaborative_mode": is_collaborative,
            "user": str(request.user),
            "user_locations": user_locations,
            "public_locations": public_locations,
            "visible_locations": all_locations,
        })

    @action(detail=False, methods=['get'])
    def filtered(self, request):
        """Filter locations by category types and visit status."""
        types = request.query_params.get('types', '').split(',')
        is_collaborative = getattr(settings, 'COLLABORATIVE_MODE', False)

        logger.info(f"[filtered] User: {request.user}, types: {types}, collaborative: {is_collaborative}")

        # Get base queryset using the same method as map_locations for consistency
        queryset = Location.objects.retrieve_locations(
            request.user,
            include_owned=True,
            include_shared=True,
            include_public=is_collaborative
        )

        logger.info(f"[filtered] Base queryset count: {queryset.count()}")

        # Filter by category if specific types requested (not 'all')
        if 'all' not in types:
            # Build category filter based on collaborative mode
            if is_collaborative:
                user_category_filter = Q(is_global=True) | Q(user=request.user)
            else:
                user_category_filter = Q(user=request.user)

            # Validate provided types against user's accessible categories
            valid_categories = Category.objects.filter(user_category_filter, name__in=types)
            if not valid_categories.exists():
                logger.warning(f"[filtered] No valid categories found for types: {types}")
                return Response(
                    {"error": "Invalid category or no types provided"},
                    status=400
                )

            # Filter by category name to include all locations with matching category names
            queryset = queryset.filter(category__name__in=types)
            logger.info(f"[filtered] After category filter count: {queryset.count()}")

        # Apply visit status filtering
        queryset = self._apply_visit_filtering(queryset, request)
        # Apply visibility filtering
        queryset = self._apply_public_filtering(queryset, request)
        # Apply ownership filtering
        queryset = self._apply_ownership_filtering(queryset, request)
        # Apply rating filtering
        queryset = self._apply_rating_filtering(queryset, request)
        queryset = self.apply_sorting(queryset)

        return self.paginate_and_respond(queryset, request)

    @action(detail=False, methods=['get'])
    def all(self, request):
        """Get all locations (public and owned) with optional collection filtering."""
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)

        include_collections = request.query_params.get('include_collections', 'false') == 'true'
        nested = request.query_params.get('nested', 'false') == 'true'
        allowedNestedFields = request.query_params.get('allowed_nested_fields', '').split(',')

        # Use retrieve_locations with collaborative mode support
        queryset = Location.objects.retrieve_locations(
            request.user,
            include_owned=True,
            include_shared=include_collections,
            include_public=getattr(settings, 'COLLABORATIVE_MODE', False)
        )

        if not include_collections:
            queryset = queryset.filter(collections__isnull=True)

        queryset = self.apply_sorting(queryset)
        serializer = self.get_serializer(queryset, many=True, context={'nested': nested, 'allowed_nested_fields': allowedNestedFields, 'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """Return a lightweight payload for calendar rendering."""
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)

        queryset = (
            self.get_queryset()
            .filter(visits__isnull=False)
            .select_related('category')
            .prefetch_related(
                Prefetch(
                    'visits',
                    queryset=Visit.objects.only('id', 'start_date', 'end_date', 'timezone')
                )
            )
            .only('id', 'name', 'location', 'category__name', 'category__icon')
            .distinct()
        )

        serializer = CalendarLocationSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='additional-info')
    def additional_info(self, request, pk=None):
        """Get adventure with additional sunrise/sunset information."""
        adventure = self.get_object()
        user = request.user

        # Validate access permissions
        if not self._has_adventure_access(adventure, user):
            return Response(
                {"error": "User does not have permission to access this adventure"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get base adventure data
        serializer = self.get_serializer(adventure)
        response_data = serializer.data

        # Add sunrise/sunset data
        response_data['sun_times'] = self._get_sun_times(adventure, response_data.get('visits', []))
        
        return Response(response_data)
    
    # view to return location name and lat/lon for all locations a user owns for the golobal map
    @action(detail=False, methods=['get'], url_path='pins')
    def map_locations(self, request):
        """Get all locations with name and lat/lon for map display."""
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)

        locations = Location.objects.retrieve_locations(
            request.user,
            include_owned=True,
            include_shared=True,
            include_public=getattr(settings, 'COLLABORATIVE_MODE', False)
        )
        serializer = MapPinSerializer(locations, many=True, context={'request': request})
        return Response(serializer.data)

    # ==================== HELPER METHODS ====================

    def _validate_collection_update_permissions(self, instance, new_collections):
        """Validate collection permissions for updates, allowing collection owners to unlink locations."""
        current_collections = set(instance.collections.all())
        new_collections_set = set(new_collections)
        
        # Collections being added
        collections_to_add = new_collections_set - current_collections
        
        # Collections being removed
        collections_to_remove = current_collections - new_collections_set
        
        # Validate permissions for collections being added
        for collection in collections_to_add:
            # Standard validation for adding collections
            if collection.user != self.request.user:
                # Check if user has shared access to the collection
                if not collection.shared_with.filter(uuid=self.request.user.uuid).exists():
                    raise PermissionDenied(
                        f"You don't have permission to add location to collection '{collection.name}'"
                    )
        
        # For collections being removed, allow if:
        # 1. User owns the location, OR
        # 2. User owns the collection (even if they don't own the location)
        for collection in collections_to_remove:
            user_owns_location = instance.user == self.request.user
            user_owns_collection = collection.user == self.request.user
            
            if not (user_owns_location or user_owns_collection):
                # Check if user has shared access to the collection
                if not collection.shared_with.filter(uuid=self.request.user.uuid).exists():
                    raise PermissionDenied(
                        f"You don't have permission to remove this location from one of the collections it's linked to.'"
                    )
            else:
                # If the removal is permitted, also remove any itinerary items
                # in this collection that reference this Location instance.
                try:
                    ct = ContentType.objects.get_for_model(instance.__class__)
                    # Try deleting by native PK type first, then by string.
                    qs = CollectionItineraryItem.objects.filter(
                        collection=collection, content_type=ct, object_id=instance.pk
                    )
                    if qs.exists():
                        qs.delete()
                    else:
                        CollectionItineraryItem.objects.filter(
                            collection=collection, content_type=ct, object_id=str(instance.pk)
                        ).delete()
                except Exception:
                    # Don't raise on cleanup failures; deletion of itinerary items
                    # is best-effort and shouldn't block the update operation.
                    pass

    def _validate_collection_permissions(self, collections):
        """Validate permissions for all collections (used in create)."""
        for collection in collections:
            if collection.user != self.request.user:
                # Check if user has shared access to the collection
                if not collection.shared_with.filter(uuid=self.request.user.uuid).exists():
                    raise PermissionDenied(
                        f"You don't have permission to add location to collection '{collection.name}'"
                    )

    # Filter methods inherited from FilteringMixin:
    # - _apply_visit_filtering
    # - _apply_public_filtering
    # - _apply_ownership_filtering
    # - _apply_rating_filtering

    def _has_adventure_access(self, adventure, user):
        """Check if user has access to adventure."""
        # Allow if public
        if adventure.is_public:
            return True

        # Check ownership
        if user.is_authenticated and adventure.user == user:
            return True

        # Check shared collection access
        if user.is_authenticated:
            for collection in adventure.collections.all():
                if collection.shared_with.filter(uuid=user.uuid).exists() or collection.user == user:
                    return True

        return False

    def _get_sun_times(self, adventure, visits):
        """Get sunrise/sunset times for adventure visits."""
        sun_times = []

        for visit in visits:
            date = visit.get('start_date')
            if not (date and adventure.longitude and adventure.latitude):
                continue

            api_url = (
                f'https://api.sunrisesunset.io/json?'
                f'lat={adventure.latitude}&lng={adventure.longitude}&date={date}'
            )
            
            try:
                response = requests.get(api_url)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', {})
                    
                    if results.get('sunrise') and results.get('sunset'):
                        sun_times.append({
                            "date": date,
                            "visit_id": visit.get('id'),
                            "sunrise": results.get('sunrise'),
                            "sunset": results.get('sunset')
                        })
            except requests.RequestException:
                # Skip this visit if API call fails
                continue

        return sun_times

    def paginate_and_respond(self, queryset, request):
        """Paginate queryset and return response."""
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)