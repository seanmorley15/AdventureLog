from django.db.models import Count, F, Q, Prefetch
from django.db.models.functions import Lower
from django.db import transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
import logging
from adventures.models import CollectionActivity
from adventures.services.activity_log import record_activity
from adventures.models import (
    Collection,
    Location,
    Transportation,
    Note,
    Checklist,
    ContentImage,
    CollectionItineraryItem,
    Lodging,
    CollectionItineraryDay,
)
from adventures.permissions import CollectionShared
from adventures.services.collections.duplicate import duplicate_collection
from adventures.views.mixins import PaginatedResponseMixin
from adventures.access.audience import audience_for_request, readable_collections_q
from adventures.utils.query_optimization import media_prefetches, optimize_locations
from adventures.services.story import build_story_payload
from adventures.serializers import (
    CollectionSerializer,
    UltraSlimCollectionSerializer,
    CollectionItineraryItemSerializer,
    CollectionItineraryDaySerializer,
)
from django.contrib.auth import get_user_model
from core import pagination
from adventures.services import day_plan

User = get_user_model()
logger = logging.getLogger(__name__)



from .exports import ExportActionsMixin
from .sharing import SharingActionsMixin


class CollectionViewSet(SharingActionsMixin, ExportActionsMixin, PaginatedResponseMixin, viewsets.ModelViewSet):
    serializer_class = CollectionSerializer
    permission_classes = [CollectionShared]
    pagination_class = pagination.StandardResultsSetPagination

    def get_serializer_class(self):
        """Return different serializers based on the action"""
        if self.action in ['list', 'all', 'archived', 'shared']:
            return UltraSlimCollectionSerializer
        return CollectionSerializer

    def apply_sorting(self, queryset):
        order_by = self.request.query_params.get('order_by', 'name')
        order_direction = self.request.query_params.get('order_direction', 'asc')

        valid_order_by = ['name', 'updated_at', 'start_date']
        if order_by not in valid_order_by:
            order_by = 'updated_at'

        if order_direction not in ['asc', 'desc']:
            order_direction = 'asc'

        descending = order_direction == 'desc'
        if order_by == 'name':
            # Case-insensitive, so "alpha" sorts with "Alpha".
            queryset = queryset.annotate(lower_name=Lower('name'))
            ordering = [F('lower_name').desc() if descending else F('lower_name').asc()]
        elif order_by == 'start_date':
            # Collections without a start date go last in either direction.
            ordering = [F('start_date').desc(nulls_last=True) if descending else F('start_date').asc(nulls_last=True)]
        else:
            ordering = [F('updated_at').desc() if descending else F('updated_at').asc()]

        return queryset.order_by(*ordering)

    def apply_status_filter(self, queryset):
        """Apply status filtering based on query parameter"""
        from datetime import date
        status_filter = self.request.query_params.get('status', None)
        
        if not status_filter:
            return queryset
        
        today = date.today()
        
        if status_filter == 'upcoming':
            # Start date in the future. Both dates are required to match lifecycle status.
            return queryset.filter(start_date__gt=today, end_date__isnull=False)
        elif status_filter == 'in_progress':
            # Currently ongoing
            return queryset.filter(start_date__lte=today, end_date__gte=today)
        elif status_filter == 'completed':
            # End date in the past
            return queryset.filter(start_date__isnull=False, end_date__lt=today)
        
        return queryset

    @staticmethod
    def _for_listing(queryset):
        """Counts and relations the list serializer reads, loaded with the page."""
        return queryset.select_related('user', 'primary_image').annotate(
            day_count_annotated=Count('itinerary_days', filter=Q(itinerary_days__index__isnull=False), distinct=True),
            location_count_annotated=Count('locations', distinct=True),
        ).prefetch_related('shared_with', 'members')

    def apply_type_filter(self, queryset):
        """Filter by collection type. type=folder replaces the old status=folder list filter."""
        type_filter = self.request.query_params.get('type')
        if type_filter in ('folder', 'trip'):
            return queryset.filter(type=type_filter)
        return queryset

    def get_serializer_context(self):
        """Override to add nested and exclusion contexts based on query parameters"""
        context = super().get_serializer_context()
        
        # Handle nested parameter (only for full serializer actions)
        if self.action not in ['list', 'all', 'archived', 'shared']:
            is_nested = self.request.query_params.get('nested', 'false').lower() == 'true'
            if is_nested:
                context['nested'] = True
            
            # Handle individual exclusion parameters (if using granular approach)
            exclude_params = [
                'exclude_transportations',
                'exclude_notes', 
                'exclude_checklists',
                'exclude_lodging'
            ]
            
            for param in exclude_params:
                if self.request.query_params.get(param, 'false').lower() == 'true':
                    context[param] = True
                    
        return context

    def get_optimized_queryset_for_listing(self):
        """Get optimized queryset for list actions with prefetching"""
        return self.get_base_queryset().select_related('user', 'primary_image').prefetch_related(
            Prefetch(
                'locations__images',
                queryset=ContentImage.objects.filter(is_primary=True).select_related('user'),
                to_attr='primary_images'
            ),
            'shared_with'
        )

    def get_base_queryset(self):
        """Base queryset logic extracted for reuse"""
        if self.action == 'destroy':
            queryset = Collection.objects.filter(user=self.request.user.id)
        elif self.action in ['update', 'partial_update']:
            queryset = Collection.objects.filter(user=self.request.user.id)
        elif self.action == 'leave':
            queryset = Collection.objects.filter(
                Q(user=self.request.user.id) | Q(shared_with=self.request.user)
            ).distinct()
        # Allow access to collections with pending invites for accept/decline actions
        elif self.action in ['accept_invite', 'decline_invite']:
            if not self.request.user.is_authenticated:
                queryset = Collection.objects.none()
            else:
                queryset = Collection.objects.filter(
                    Q(user=self.request.user.id)
                    | Q(shared_with=self.request.user)
                    | Q(invites__invited_user=self.request.user)
                ).distinct()
        elif self.action == 'export_collection':
            # An owner can always download their own collection, archived or not.
            queryset = Collection.objects.filter(user=self.request.user.id)
        elif self.action in ('retrieve', 'export_pdf', 'share_image'):
            # Members, guest links, and readers of a public or unlisted story.
            queryset = Collection.objects.filter(readable_collections_q(self.request)).distinct()
            if self.action == 'retrieve':
                queryset = queryset.prefetch_related(*self._detail_prefetches())
        else:
            # For list action and default base queryset, return collections owned by the user (exclude shared)
            queryset = Collection.objects.filter(
                Q(user=self.request.user.id) & Q(is_archived=False)
            ).distinct()

        return queryset.select_related('primary_image').prefetch_related('shared_with')

    @staticmethod
    def _detail_prefetches():
        """Everything CollectionSerializer reads, loaded in a fixed number of queries."""
        locations = optimize_locations(Location.objects.all())
        return [
            Prefetch('locations', queryset=locations),
            Prefetch(
                'transportation_set',
                queryset=Transportation.objects.select_related('user').prefetch_related(*media_prefetches()),
            ),
            Prefetch(
                'lodging_set',
                queryset=Lodging.objects.select_related('user').prefetch_related(*media_prefetches()),
            ),
            Prefetch('note_set', queryset=Note.objects.select_related('user')),
            Prefetch(
                'checklist_set',
                queryset=Checklist.objects.select_related('user').prefetch_related('checklistitem_set'),
            ),
            'members',
        ]

    def get_queryset(self):
        """Get queryset with optimizations for list actions"""
        if self.action in ['list', 'all', 'archived', 'shared']:
            return self.get_optimized_queryset_for_listing()
        return self.get_base_queryset()

    def list(self, request):
        # make sure the user is authenticated
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        
        # List should only return collections owned by the requesting user (shared collections are available
        # via the `shared` action).
        queryset = Collection.objects.filter(
            Q(user=request.user.id) & Q(is_archived=False)
        ).distinct().select_related('user', 'primary_image')
        
        queryset = self._for_listing(queryset)
        queryset = self.apply_type_filter(queryset)
        queryset = self.apply_status_filter(queryset)
        queryset = self.apply_sorting(queryset)
        return self.paginate_and_respond(queryset, request)

    @action(detail=False, methods=['get'])
    def all(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
       
        queryset = Collection.objects.filter(
            Q(user=request.user)
        ).select_related('user', 'primary_image')
        
        queryset = self.apply_sorting(self._for_listing(queryset))
        serializer = self.get_serializer(queryset, many=True)
       
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def archived(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
       
        queryset = Collection.objects.filter(
            Q(user=request.user.id) & Q(is_archived=True)
        ).select_related('user', 'primary_image')
        
        queryset = self.apply_sorting(self._for_listing(queryset))
        serializer = self.get_serializer(queryset, many=True)
       
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """
        Retrieve a collection and include itinerary items and day metadata in the response.

        A public reader gets the story payload only. A member can ask for the same
        payload with ``?as=story`` to preview what people with the link see.
        """
        collection = self.get_object()
        audience = audience_for_request(request, collection)
        story_mode = audience.is_public_reader or request.query_params.get('as') == 'story'
        context = self.get_serializer_context()
        if story_mode:
            # The story whitelist drops most of the member payload. Skip building the
            # expensive parts (Wanderer lookups, GeoJSON) rather than build and discard.
            context = {**context, 'story': True, 'story_gpx': collection.story_group('gpx')}
        serializer = CollectionSerializer(collection, context=context)
        data = serializer.data

        # Include itinerary items inline with collection details
        # prefetch_related('item') resolves each placement's target with one query per type.
        itinerary_items = (
            CollectionItineraryItem.objects.filter(collection=collection)
            .select_related('day', 'content_type')
            .prefetch_related('item')
        )
        itinerary_serializer = CollectionItineraryItemSerializer(itinerary_items, many=True)
        data['itinerary'] = itinerary_serializer.data
        
        # Include itinerary day metadata
        itinerary_days = CollectionItineraryDay.objects.filter(collection=collection)
        days_serializer = CollectionItineraryDaySerializer(itinerary_days, many=True)
        data['itinerary_days'] = days_serializer.data
        from adventures.services.day_plan.files import serialize_day_files

        data.update(serialize_day_files(collection, context))

        if story_mode:
            story = build_story_payload(data, collection)
            story['audience'] = audience.as_dict()
            story['story_preview'] = not audience.is_public_reader
            return Response(story)
        return Response(data)

    @action(detail=False, methods=['get'])
    def shared(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        
        queryset = Collection.objects.filter(
            shared_with=request.user
        ).select_related('user')
        
        queryset = self.apply_sorting(self._for_listing(queryset))
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Create a private copy of a collection (see ``duplicate_collection``). Only the owner can."""
        original = self.get_object()

        if original.user != request.user:
            return Response(
                {"error": "You do not have permission to duplicate this collection."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            new_collection = duplicate_collection(original, request.user)
        except Exception:
            logger.exception("Failed to duplicate collection %s", pk)
            return Response(
                {"error": "An error occurred while duplicating the collection."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(self.get_serializer(new_collection).data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        # This is ok because you cannot share a collection when creating it
        serializer.save(user=self.request.user)

    def _cleanup_out_of_range_itinerary_items(self, collection):
        """Delete itinerary items and day metadata outside a date-keyed collection's range."""
        if not collection.start_date or not collection.end_date:
            # If no date range is set, don't delete anything
            return
        if day_plan.is_day_based(collection):
            # Day-based trips are keyed by index; their dates are only projections.
            return
        
        # Delete itinerary items outside the date range
        deleted_items = CollectionItineraryItem.objects.filter(
            collection=collection
        ).exclude(
            date__range=[collection.start_date, collection.end_date]
        ).delete()
        
        # Delete day metadata outside the date range
        deleted_days = CollectionItineraryDay.objects.filter(
            collection=collection
        ).exclude(
            date__range=[collection.start_date, collection.end_date]
        ).delete()
        
        return deleted_items, deleted_days

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """
        Update the collection and clean up out-of-range itinerary items when dates change.

        Visibility does not cascade. Publishing a collection does not change
        ``is_public`` on its locations, lodging, transport, notes, or checklists,
        and making it private does not change them either.
        """
        instance = self.get_object()
        old_start_date = instance.start_date
        old_end_date = instance.end_date
        old_type = instance.type
        
        # Perform the standard update
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if serializer.instance.start_date != old_start_date:
            record_activity(
                serializer.instance, request, CollectionActivity.Verb.ANCHOR_CHANGED,
                from_date=old_start_date.isoformat() if old_start_date else None,
                to_date=serializer.instance.start_date.isoformat() if serializer.instance.start_date else None,
            )
        
        if old_type != serializer.instance.type:
            day_plan.apply_type_change(serializer.instance, old_type)

        # Check if dates changed
        new_start_date = serializer.instance.start_date
        new_end_date = serializer.instance.end_date
        
        dates_changed = (old_start_date != new_start_date or old_end_date != new_end_date)
        # A folder that just became a trip keeps Ideas rows, which have no date.
        became_trip = old_type == 'folder' and serializer.instance.type == 'trip'

        # Clean up out-of-range items if dates changed
        if dates_changed and not became_trip:
            self._cleanup_out_of_range_itinerary_items(serializer.instance)
        
        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}
        
        return Response(serializer.data)
