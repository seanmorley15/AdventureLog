from django.utils import timezone
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Max
from django.db.models.functions import Lower
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
import requests

from adventures.models import Adventure, Category, Transportation, Lodging
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from adventures.serializers import AdventureSerializer, TransportationSerializer, LodgingSerializer
from adventures.utils import pagination


class AdventureViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Adventure objects with support for filtering, sorting,
    and sharing functionality.
    """
    serializer_class = AdventureSerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess]
    pagination_class = pagination.StandardResultsSetPagination

    # ==================== QUERYSET & PERMISSIONS ====================

    def get_queryset(self):
        """
        Returns queryset based on user authentication and action type.
        Public actions allow unauthenticated access to public adventures.
        """
        user = self.request.user
        public_allowed_actions = {'retrieve', 'additional_info'}

        if not user.is_authenticated:
            if self.action in public_allowed_actions:
                return Adventure.objects.retrieve_adventures(
                    user, include_public=True
                ).order_by('-updated_at')
            return Adventure.objects.none()

        include_public = self.action in public_allowed_actions
        return Adventure.objects.retrieve_adventures(
            user,
            include_public=include_public,
            include_owned=True,
            include_shared=True
        ).order_by('-updated_at')

    # ==================== SORTING & FILTERING ====================

    def apply_sorting(self, queryset):
        """Apply sorting and collection filtering to queryset."""
        order_by = self.request.query_params.get('order_by', 'updated_at')
        order_direction = self.request.query_params.get('order_direction', 'asc')
        include_collections = self.request.query_params.get('include_collections', 'true')

        # Validate parameters
        valid_order_by = ['name', 'type', 'date', 'rating', 'updated_at']
        if order_by not in valid_order_by:
            order_by = 'name'

        if order_direction not in ['asc', 'desc']:
            order_direction = 'asc'

        # Apply sorting logic
        queryset = self._apply_ordering(queryset, order_by, order_direction)

        # Filter adventures without collections if requested
        if include_collections == 'false':
            queryset = queryset.filter(collections__isnull=True)

        return queryset

    def _apply_ordering(self, queryset, order_by, order_direction):
        """Apply ordering to queryset based on field type."""
        if order_by == 'date':
            queryset = queryset.annotate(
                latest_visit=Max('visits__start_date')
            ).filter(latest_visit__isnull=False)
            ordering = 'latest_visit'
        elif order_by == 'name':
            queryset = queryset.annotate(lower_name=Lower('name'))
            ordering = 'lower_name'
        elif order_by == 'rating':
            queryset = queryset.filter(rating__isnull=False)
            ordering = 'rating'
        elif order_by == 'updated_at':
            # Special handling for updated_at (reverse default order)
            ordering = '-updated_at' if order_direction == 'asc' else 'updated_at'
            return queryset.order_by(ordering)
        else:
            ordering = order_by

        # Apply direction
        if order_direction == 'desc':
            ordering = f'-{ordering}'

        return queryset.order_by(ordering)

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

        serializer.save(user_id=user_to_assign)

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

    # ==================== CUSTOM ACTIONS ====================

    @action(detail=False, methods=['get'])
    def filtered(self, request):
        """Filter adventures by category types and visit status."""
        types = request.query_params.get('types', '').split(',')
        
        # Handle 'all' types
        if 'all' in types:
            types = Category.objects.filter(
                user_id=request.user
            ).values_list('name', flat=True)
        else:
            # Validate provided types
            if not types or not all(
                Category.objects.filter(user_id=request.user, name=type_name).exists() 
                for type_name in types
            ):
                return Response(
                    {"error": "Invalid category or no types provided"}, 
                    status=400
                )

        # Build base queryset
        queryset = Adventure.objects.filter(
            category__in=Category.objects.filter(name__in=types, user_id=request.user),
            user_id=request.user.id
        )

        # Apply visit status filtering
        queryset = self._apply_visit_filtering(queryset, request)
        queryset = self.apply_sorting(queryset)
        
        return self.paginate_and_respond(queryset, request)

    @action(detail=False, methods=['get'])
    def all(self, request):
        """Get all adventures (public and owned) with optional collection filtering."""
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)

        include_collections = request.query_params.get('include_collections', 'false') == 'true'
        
        # Build queryset with collection filtering
        base_filter = Q(user_id=request.user.id)
        
        if include_collections:
            queryset = Adventure.objects.filter(base_filter)
        else:
            queryset = Adventure.objects.filter(base_filter, collections__isnull=True)

        queryset = self.apply_sorting(queryset)
        serializer = self.get_serializer(queryset, many=True)
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

    # ==================== HELPER METHODS ====================

    def _validate_collection_permissions(self, collections):
        """Validate user has permission to use all provided collections. Only the owner or shared users can use collections."""
        for collection in collections:
            if not (collection.user_id == self.request.user or 
                   collection.shared_with.filter(uuid=self.request.user.uuid).exists()):
                raise PermissionDenied(
                    f"You do not have permission to use collection '{collection.name}'."
                )

    def _validate_collection_update_permissions(self, instance, new_collections):
        """Validate permissions for collection updates (add/remove)."""
        # Check permissions for new collections being added
        for collection in new_collections:
            if (collection.user_id != self.request.user and 
                not collection.shared_with.filter(uuid=self.request.user.uuid).exists()):
                raise PermissionDenied(
                    f"You do not have permission to use collection '{collection.name}'."
                )

        # Check permissions for collections being removed
        current_collections = set(instance.collections.all())
        new_collections_set = set(new_collections)
        collections_to_remove = current_collections - new_collections_set

        for collection in collections_to_remove:
            if (collection.user_id != self.request.user and 
                not collection.shared_with.filter(uuid=self.request.user.uuid).exists()):
                raise PermissionDenied(
                    f"You cannot remove the adventure from collection '{collection.name}' "
                    f"as you don't have permission."
                )

    def _apply_visit_filtering(self, queryset, request):
        """Apply visit status filtering to queryset."""
        is_visited_param = request.query_params.get('is_visited')
        if is_visited_param is None:
            return queryset

        # Convert parameter to boolean
        if is_visited_param.lower() == 'true':
            is_visited_bool = True
        elif is_visited_param.lower() == 'false':
            is_visited_bool = False
        else:
            return queryset

        # Apply visit filtering
        now = timezone.now().date()
        if is_visited_bool:
            queryset = queryset.filter(visits__start_date__lte=now).distinct()
        else:
            queryset = queryset.exclude(visits__start_date__lte=now).distinct()

        return queryset

    def _has_adventure_access(self, adventure, user):
        """Check if user has access to adventure."""
        # Allow if public
        if adventure.is_public:
            return True

        # Check ownership
        if user.is_authenticated and adventure.user_id == user:
            return True

        # Check shared collection access
        if user.is_authenticated:
            for collection in adventure.collections.all():
                if collection.shared_with.filter(uuid=user.uuid).exists():
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