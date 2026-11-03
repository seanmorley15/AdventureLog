from django.db.models import Count, F, Q, Prefetch
from django.db.models.functions import Lower
from django.db import transaction
from drf_spectacular.utils import (
    OpenApiParameter,
    PolymorphicProxySerializer,
    extend_schema,
    extend_schema_view,
)
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
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
from adventures.serializers.collection_detail import (
    CollectionDetailSerializer,
    CollectionListQuerySerializer,
    CollectionStorySerializer,
)
from django.contrib.auth import get_user_model
from core import pagination
from core.exceptions import APIError
from core.serializers import validated
from adventures.services import day_plan

User = get_user_model()
logger = logging.getLogger(__name__)



from .exports import ExportActionsMixin
from .sharing import SharingActionsMixin


@extend_schema_view(
    create=extend_schema(
        description='Create a folder or a trip. A collection with dates, or `type: trip`, is a trip with a day '
        'plan; send `day_count` (or `end_date`) to set its length.',
    ),
    update=extend_schema(
        description='Owner only. Changing the dates of a dated trip removes placements outside the new range. '
        'Changing `visibility` does not change the records inside.',
    ),
    partial_update=extend_schema(description='Owner only. Like PUT, for the fields you send.'),
    destroy=extend_schema(description='Owner only. Deletes the collection; records in it that belong to you stay.'),
)
class CollectionViewSet(SharingActionsMixin, ExportActionsMixin, PaginatedResponseMixin, viewsets.ModelViewSet):
    """
    Collections group places, stays, journeys, notes and checklists. A **folder** is a plain group;
    a **trip** has dates or a number of days and a day plan.

    The owner can share a collection with other users as editors or viewers, hand out guest
    links, and publish it as a story (`visibility`: `private`, `unlisted` or `public`).
    """

    openapi_tags = ['Collections']
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
    permission_classes = [CollectionShared]
    pagination_class = pagination.StandardResultsSetPagination

    def get_serializer_class(self):
        """Return different serializers based on the action"""
        if self.action == 'list':
            return UltraSlimCollectionSerializer
        return CollectionSerializer

    @staticmethod
    def apply_sorting(queryset, ordering):
        descending = ordering.startswith('-')
        order_by = ordering.lstrip('-')
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

    @staticmethod
    def apply_status_filter(queryset, status_filter):
        """Filter by where today falls relative to the trip dates."""
        from datetime import date

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
        elif self.action == 'archive':
            # An owner can always download their own collection, archived or not.
            queryset = Collection.objects.filter(user=self.request.user.id)
        elif self.action in ('retrieve', 'pdf', 'share_image'):
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
        if getattr(self, 'swagger_fake_view', False):
            return Collection.objects.none()
        return self.get_base_queryset()

    @extend_schema(parameters=[CollectionListQuerySerializer], responses=UltraSlimCollectionSerializer(many=True))
    def list(self, request):
        """
        List collections

        Your collections, or with `membership=shared` the ones shared with you, a page at a
        time, as cards (no records inside).
        """
        params = validated(CollectionListQuerySerializer, request.query_params)
        if params['membership'] == 'shared':
            queryset = Collection.objects.filter(shared_with=request.user)
            if params['archived'] is not None:
                queryset = queryset.filter(is_archived=params['archived'])
        else:
            archived = params['archived'] if params['archived'] is not None else False
            queryset = Collection.objects.filter(user=request.user, is_archived=archived)

        queryset = self._for_listing(queryset.distinct())
        if params.get('type'):
            queryset = queryset.filter(type=params['type'])
        queryset = self.apply_status_filter(queryset, params.get('status'))
        queryset = self.apply_sorting(queryset, params['ordering'])
        return self.paginate_and_respond(queryset, request)

    @extend_schema(
        parameters=[
            OpenApiParameter('as', str, enum=['story'], description='`story`: preview what people with the public '
                             'link see.'),
            OpenApiParameter('s', str, description='The share secret, to read an unlisted collection.'),
        ],
        responses=PolymorphicProxySerializer(
            component_name='CollectionRetrieve',
            serializers=[CollectionDetailSerializer, CollectionStorySerializer],
            resource_type_field_name=None,
        ),
    )
    def retrieve(self, request, pk=None):
        """
        Get a collection

        Members get the whole collection with its records and day plan. Anyone else who can
        read it (a public or unlisted story, or a guest link with `X-Guest-Token`) gets the
        story instead. Members can ask for the story with `as=story` to preview it.
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

    @extend_schema(request=None, responses={201: CollectionSerializer})
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """
        Copy a collection

        Owner only. Makes a private copy with everything in it and its day plan, without the
        members or guest links.
        """
        original = self.get_object()
        if original.user != request.user:
            raise PermissionDenied('Only the owner can copy this collection.')
        try:
            new_collection = duplicate_collection(original, request.user)
        except Exception:
            logger.exception("Failed to duplicate collection %s", pk)
            raise APIError('The collection could not be copied.', code='server_error', status=500)
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
