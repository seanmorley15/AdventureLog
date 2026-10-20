import logging
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q, Max, Prefetch, Exists, OuterRef, F
from django.contrib.gis.db.models.functions import Distance
from django.db.models.functions import Lower
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from adventures.models import Location, Category, Collection, ContentImage, Visit
from adventures.permissions import IsOwnerOrSharedWithFullAccess, ensure_can_add_to_collections
from adventures.access.audience import can_edit, is_member, member_collections_q, member_role, readable_collections_q
from adventures.access.location import can_read_location
from adventures.services.location_collections import link_location, placements_for, unlink_location
from adventures.utils.query_optimization import optimize_locations
from adventures.serializers import (
    add_quick_add_extras,
    CalendarLocationSerializer,
    LocationListSerializer,
    LocationSerializer,
    MapPinSerializer,
)
from core import pagination
from adventures.throttling import ExternalGeocodeThrottle
from adventures.services.exports.share_image import (
    build_share_image,
    get_location_for_share,
    resolve_share_page_url,
    share_image_filename,
    valid_aspect,
)
from adventures.services.locations.center import collection_center
from adventures.services.locations.copy import copy_location
from adventures.services.locations.matching import find_duplicate_locations
from adventures.views.mixins import PaginatedResponseMixin
from adventures.services.geocoding.assignment import apply_reverse_geocode_result
from adventures.services.quick_add import (
    QuickAddError,
    finish_quick_add,
    prepare_location_quick_add,
)

logger = logging.getLogger(__name__)


# Fields of a place record that only its owner changes. They appear in every
# collection the place is linked to, so a collaborator edit would leak across trips.
OWNER_ONLY_LOCATION_FIELDS = (
    'name', 'description', 'category', 'is_public', 'location',
    'latitude', 'longitude', 'coordinates',
)

class LocationViewSet(PaginatedResponseMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing Adventure objects with support for filtering, sorting,
    and sharing functionality.
    """
    serializer_class = LocationSerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess]
    pagination_class = pagination.StandardResultsSetPagination

    # ==================== QUERYSET & PERMISSIONS ====================

    def get_queryset(self):
        """
        Returns queryset based on user authentication and action type.
        Public actions allow unauthenticated access to public locations.
        """
        user = self.request.user
        public_allowed_actions = {'retrieve', 'additional_info', 'share_image'}

        if not user.is_authenticated:
            if self.action in public_allowed_actions:
                return Location.objects.retrieve_locations(
                    user, include_public=True
                ).order_by('-updated_at')
            return Location.objects.none()

        include_public = self.action in public_allowed_actions
        queryset = Location.objects.retrieve_locations(
            user,
            include_public=include_public,
            include_owned=True,
            include_shared=True
        ).order_by('-updated_at')
        # Lists serialize many places; load what they read in a fixed number of queries.
        if self.action == 'list':
            queryset = optimize_locations(queryset)
        return queryset

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

        # Filter locations without collections if requested
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
            # The locations page sends one direction for every field and defaults it to 'asc', so
            # 'asc' on updated_at must mean newest first for its default view to show recent places.
            # (Collections use plain ascending and descending.) Change this together with the page.
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

        # A place created inside a collection belongs to the collection owner,
        # including when a collaborator creates it. Their own map does not gain the pin.
        user_to_assign = collections[0].user if collections else self.request.user

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

        # The place record belongs to its owner and shows up in every collection.
        # A collaborator changes placements, visits, and photos, not these fields.
        if instance.user_id != request.user.id:
            for field in OWNER_ONLY_LOCATION_FIELDS:
                serializer.validated_data.pop(field, None)

        removed_collections = []
        if 'collections' in serializer.validated_data:
            requested = list(serializer.validated_data['collections'])
            # A PATCH only changes collections the requester can open; links to
            # others stay, so a stale or partial list cannot drop them.
            visible = Collection.objects.filter(
                pk__in=instance.collections.values_list('pk', flat=True)
            ).filter(readable_collections_q(request))
            hidden = list(instance.collections.exclude(pk__in=visible.values_list('pk', flat=True)))
            serializer.validated_data['collections'] = requested + [
                c for c in hidden if c not in requested
            ]
            removed_collections = self._validate_collection_update_permissions(
                instance, serializer.validated_data['collections']
            )
        else:
            # Remove collections from validated_data if not provided
            serializer.validated_data.pop('collections', None)

        with transaction.atomic():
            self.perform_update(serializer)
            for collection in removed_collections:
                unlink_location(instance, collection)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Only allow the owner to delete a location."""
        instance = self.get_object()
        
        # Check if the user is the owner
        if instance.user != request.user:
            raise PermissionDenied("Only the owner can delete this location.")
        
        return super().destroy(request, *args, **kwargs)

    # ==================== CUSTOM ACTIONS ====================

    @action(
        detail=False,
        methods=['post'],
        url_path='quick-add',
        throttle_classes=[ExternalGeocodeThrottle],
    )
    def quick_add(self, request):
        """Create a location from lightweight map/place input in one server-side call."""
        payload = request.data if isinstance(request.data, dict) else {}

        try:
            # Anything that fails inside rolls the whole thing back, so a refusal leaves no half-made place.
            with transaction.atomic():
                prepared = prepare_location_quick_add(
                    request.user, payload, can_add_to_collection=lambda collection: can_edit(request, collection)
                )
                serializer = self.get_serializer(data=prepared.serializer_payload)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)

                location = serializer.instance
                apply_reverse_geocode_result(location, prepared.reverse_data, prepared.location_label)
                itinerary_item, image_import_summary = finish_quick_add(location, prepared, payload)
        except QuickAddError as error:
            return Response({"error": error.message}, status=error.status_code)

        response_data = add_quick_add_extras(
            self.get_serializer(location).data, itinerary_item, image_import_summary
        )
        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='check-duplicates')
    def check_duplicates(self, request):
        """Return likely existing locations that match a place being added."""
        if not request.user or not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        payload = request.data if isinstance(request.data, dict) else {}
        name = str(payload.get('name') or '').strip()
        if not name and payload.get('latitude') in (None, '') and payload.get('longitude') in (None, ''):
            return Response(
                {"error": "name or coordinates are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        matches = find_duplicate_locations(
            request.user,
            name=name,
            latitude=payload.get('latitude'),
            longitude=payload.get('longitude'),
            location=payload.get('location'),
            exclude_id=payload.get('exclude_id') or None,
        )
        return Response({"matches": [match.to_dict() for match in matches]})

    @action(detail=False, methods=['get'])
    def filtered(self, request):
        """Filter locations by category types and visit status."""
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)

        types = [t for t in request.query_params.get('types', '').split(',') if t]
        
        # Handle 'all' types
        if 'all' in types:
            types = list(
                Category.objects.filter(user=request.user).values_list('name', flat=True)
            )
        else:
            # Validate provided types in a single query
            if not types:
                return Response(
                    {"error": "Invalid category or no types provided"},
                    status=400
                )
            found = set(
                Category.objects.filter(
                    user=request.user, name__in=types
                ).values_list('name', flat=True)
            )
            if found != set(types):
                return Response(
                    {"error": "Invalid category or no types provided"},
                    status=400
                )

        now = timezone.now()

        # Build base queryset optimized for list cards (no GPX/trails/geo payloads)
        queryset = (
            Location.objects.filter(
                category__name__in=types,
                category__user=request.user,
                user=request.user.id,
            )
            .annotate(
                annotated_is_visited=Exists(
                    Visit.objects.filter(
                        location_id=OuterRef('pk'),
                        start_date__lte=now,
                    )
                )
            )
            .select_related('category', 'user')
            .prefetch_related(
                Prefetch(
                    'images',
                    queryset=ContentImage.objects.select_related('user'),
                ),
                'collections',
            )
        )

        # Apply visit status filtering
        queryset = self._apply_visit_filtering(queryset, request)
        queryset = self.apply_sorting(queryset)

        return self.paginate_and_respond(
            queryset, request, serializer_class=LocationListSerializer
        )

    @action(detail=False, methods=['get'])
    def all(self, request):
        """Get all locations (public and owned) with optional collection filtering."""
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)

        include_collections = request.query_params.get('include_collections', 'false') == 'true'
        nested = request.query_params.get('nested', 'false') == 'true'
        allowedNestedFields = request.query_params.get('allowed_nested_fields', '').split(',')
        
        # Build queryset with collection filtering
        base_filter = Q(user=request.user.id)
        
        if include_collections:
            queryset = Location.objects.filter(base_filter)
        else:
            queryset = Location.objects.filter(base_filter, collections__isnull=True)

        queryset = optimize_locations(self.apply_sorting(queryset))
        serializer = self.get_serializer(queryset, many=True, context={'nested': nested, 'allowed_nested_fields': allowedNestedFields})
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
        """Get adventure with extended details (kept for backwards compatibility)."""
        adventure = self.get_object()
        if not can_read_location(request, adventure):
            return Response(
                {"error": "User does not have permission to access this adventure"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(adventure)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Copy a place the user can read into their own account (see ``copy_location``)."""
        original = self.get_object()

        if not can_read_location(request, original):
            return Response(
                {"error": "You do not have permission to duplicate this location."},
                status=status.HTTP_403_FORBIDDEN,
            )

        collection = None
        collection_id = request.data.get('collection_id')
        if collection_id:
            try:
                collection = Collection.objects.get(id=collection_id)
            except Collection.DoesNotExist:
                return Response({"error": "Collection not found."}, status=status.HTTP_404_NOT_FOUND)
            if not can_edit(request, collection):
                return Response(
                    {"error": "You do not have permission to add locations to this collection."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        try:
            new_location = copy_location(original, request.user, collection)
        except Exception:
            logger.exception("Failed to duplicate location %s", pk)
            return Response(
                {"error": "An error occurred while duplicating the location."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(self.get_serializer(new_location).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=['get'],
        url_path=r'share-image/(?P<aspect>square|story|landscape)',
    )
    def share_image(self, request, pk=None, aspect=None):
        """Generate a branded PNG share card for social media."""
        if not valid_aspect(aspect):
            return Response({'error': 'Invalid aspect ratio.'}, status=status.HTTP_400_BAD_REQUEST)

        location = self.get_object()
        try:
            location = get_location_for_share(location.id)
            page_url = resolve_share_page_url(request, f'/locations/{location.id}')
            png_bytes = build_share_image(location, aspect, page_url)
        except Exception:
            logger.exception('Failed to generate share image for location %s', location.id)
            return Response(
                {'error': 'Failed to generate share image. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        filename = share_image_filename(location, aspect)
        disposition = 'attachment' if request.query_params.get('download') else 'inline'
        response = HttpResponse(png_bytes, content_type='image/png')
        response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
        return response

    # view to return location name and lat/lon for all locations a user owns for the golobal map
    @action(detail=False, methods=['get'], url_path='pins')
    def map_locations(self, request):
        """Get all locations with name and lat/lon for map display."""
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)

        locations = (
            Location.objects.filter(user=request.user)
            .select_related('category__user')
            .prefetch_related('visits')
        )
        serializer = MapPinSerializer(locations, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='suggest')
    def suggest(self, request):  # the user's own places, searchable and paged
        """
        The user's own places, a page at a time.

        With ``q`` (two or more characters) search by name. Otherwise list every
        place, nearest the collection's geometric median first when a
        ``collection`` is given and has a center, A to Z when not. ``offset``
        and ``limit`` (at most 50) page through the list.
        """
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        query = str(request.query_params.get('q') or '').strip()
        try:
            limit = int(request.query_params.get('limit') or 24)
            offset = int(request.query_params.get('offset') or 0)
        except (TypeError, ValueError):
            limit, offset = 24, 0
        limit = min(max(limit, 1), 50)
        offset = max(offset, 0)


        center = None
        collection_id = request.query_params.get('collection')
        if collection_id:
            collection = Collection.objects.filter(id=collection_id).first()
            if collection is None:
                return Response({'error': 'Collection not found'}, status=status.HTTP_404_NOT_FOUND)
            if not is_member(request, collection):
                return Response({'error': 'You do not have access to this collection.'}, status=status.HTTP_403_FORBIDDEN)
            center = collection_center(collection)

        locations = Location.objects.filter(user=request.user).select_related('category')
        if len(query) >= 2:
            locations = locations.filter(name__icontains=query)

        total = locations.count()
        if center is not None:
            locations = locations.annotate(distance=Distance('coordinates', center)).order_by(
                F('distance').asc(nulls_last=True), 'name'
            )
        else:
            locations = locations.order_by('name')

        return Response({
            'results': MapPinSerializer(locations[offset:offset + limit], many=True).data,
            'anchored': center is not None,
            'total': total,
            'has_more': offset + limit < total,
        })

    # ==================== COLLECTION MEMBERSHIP ====================

    def _location_owner_fits(self, location, collection):
        """The place owner must own the collection or be a member of it."""
        return (
            collection.user_id == location.user_id
            or collection.shared_with.filter(id=location.user_id).exists()
        )

    @action(detail=True, methods=['get'], url_path='collections')
    def collection_memberships(self, request, pk=None):
        """Collections this place is in, plus the ones the requester may add it to."""
        location = self.get_object()
        query = (request.query_params.get('q') or '').strip()

        linked_ids = set(location.collections.values_list('pk', flat=True))
        candidates = Collection.objects.filter(
            Q(pk__in=linked_ids) & readable_collections_q(request)
            | member_collections_q(request, editable=True)
        ).distinct().select_related('user')
        if query:
            candidates = candidates.filter(name__icontains=query)

        rows = []
        for collection in candidates:
            role = member_role(collection, request.user)
            is_linked = collection.pk in linked_ids
            editable = can_edit(request, collection)
            rows.append({
                'id': str(collection.pk),
                'name': collection.name,
                'start_date': collection.start_date,
                'end_date': collection.end_date,
                'is_shared': collection.user_id != request.user.id,
                'owner_name': collection.user.username,
                'role': role,
                'is_linked': is_linked,
                'can_link': editable and self._location_owner_fits(location, collection),
                'can_unlink': editable or location.user_id == request.user.id,
                'placements': placements_for(location, collection) if is_linked else [],
            })
        rows.sort(key=lambda r: (
            not r['is_linked'], r['is_shared'], (r['name'] or '').lower()
        ))
        return Response(rows)

    @action(detail=True, methods=['post', 'delete'], url_path=r'collections/(?P<collection_id>[^/.]+)')
    def collection_membership(self, request, pk=None, collection_id=None):
        """Link (POST) or unlink (DELETE) this place for one collection. Idempotent."""
        location = self.get_object()
        try:
            collection = Collection.objects.get(pk=collection_id)
        except (Collection.DoesNotExist, ValidationError, ValueError):
            return Response({'error': 'Collection not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Hide collections the requester cannot open
        if not Collection.objects.filter(pk=collection.pk).filter(readable_collections_q(request)).exists():
            return Response({'error': 'Collection not found.'}, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'POST':
            if not can_edit(request, collection):
                raise PermissionDenied("You don't have permission to add locations to this collection.")
            if not self._location_owner_fits(location, collection):
                return Response(
                    {'error': 'The location owner must own or be a member of this collection.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            link_location(location, collection)
            return Response({'linked': True})

        if not (can_edit(request, collection) or location.user_id == request.user.id):
            raise PermissionDenied("You don't have permission to remove this location from the collection.")
        removed = unlink_location(location, collection)
        return Response({'linked': False, 'removed_placements': removed})

    # ==================== HELPER METHODS ====================

    def _validate_collection_update_permissions(self, instance, new_collections):
        """Check collection permissions for an update. Returns the collections being removed."""
        current_collections = set(instance.collections.all())
        new_collections_set = set(new_collections)
        
        # Collections being added
        collections_to_add = new_collections_set - current_collections
        
        # Collections being removed
        collections_to_remove = current_collections - new_collections_set
        
        # Validate permissions for collections being added
        for collection in collections_to_add:
            # Standard validation for adding collections
            if not can_edit(self.request, collection):
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
                # Editors may unlink; viewers may not
                if not can_edit(self.request, collection):
                    raise PermissionDenied(
                        "You don't have permission to remove this location from one of the collections it's linked to."
                    )

        return list(collections_to_remove)

    def _validate_collection_permissions(self, collections):
        """Validate permissions for all collections (used in create)."""
        ensure_can_add_to_collections(self.request, collections, 'location')

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
