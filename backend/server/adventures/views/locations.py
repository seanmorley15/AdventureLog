import logging

from django.contrib.gis.db.models.functions import Distance
from django.db import transaction
from django.db.models import Count, F, Max, Prefetch, Q
from django.db.models.functions import Lower
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from adventures.access.audience import EDITOR, can_edit, is_member, member_collections_q, member_role, readable_collections_q
from adventures.access.location import can_read_location
from adventures.models import Collection, ContentImage, Location
from adventures.permissions import IsOwnerOrSharedWithFullAccess, ensure_can_add_to_collections
from adventures.serializers.activity import TravelerSerializer
from adventures.serializers import LocationListSerializer, LocationSerializer, MapPinSerializer, add_quick_add_extras
from adventures.serializers.location import (
    CollectionLinkResultSerializer,
    CollectionMembershipQuerySerializer,
    CollectionMembershipSerializer,
    DuplicateCheckResultSerializer,
    DuplicateCheckSerializer,
    LocationDuplicateRequestSerializer,
    LocationListQuerySerializer,
    LocationSuggestQuerySerializer,
    LocationSuggestResponseSerializer,
    ShareImageQuerySerializer,
    SunTimesQuerySerializer,
    SunTimesSerializer,
    TravelerCandidatesQuerySerializer,
)
from adventures.serializers.sharing import UnlinkPreviewSerializer
from adventures.serializers.quick_add import LocationQuickAddResultSerializer, QuickAddSerializer
from adventures.services.exports.share_image import (
    build_share_image,
    get_location_for_share,
    resolve_share_page_url,
    share_image_filename,
)
from adventures.services.geocoding.assignment import apply_reverse_geocode_result
from adventures.services.location_collections import link_location, placements_for, unlink_location
from adventures.services.locations.center import collection_center
from adventures.services.locations.copy import copy_location, shared_file_names
from adventures.services.locations.matching import find_duplicate_locations
from adventures.services.media_quota import ensure_room_for_names
from adventures.services.quick_add import finish_quick_add, prepare_location_quick_add
from adventures.services.travelers import candidates, creator_may_delete, lost_access_plan, release_summary, take_my_visits, visited_by, where_ive_been_q
from adventures.services.sunrise_sunset.times import get_sunrise_sunset_for_date
from adventures.throttling import ExternalGeocodeThrottle, ExternalSunriseSunsetThrottle, SharingPreviewThrottle
from adventures.utils.language import resolve_request_language
from adventures.utils.query_optimization import optimize_locations
from adventures.views.mixins import PaginatedResponseMixin, preview_response, refuse_anonymous_preview
from core.visibility import can_read_published
from core import pagination
from core.errors import ServiceError
from core.exceptions import APIError
from core.openapi import ErrorSerializer
from core.geo import point_to_lat_lon
from core.parsing import as_uuid
from core.serializers import validated
from core.sync import ClientIdsMixin, ConditionalWritesMixin

logger = logging.getLogger(__name__)


# Fields of a place record that only its owner changes. They appear in every
# collection the place is linked to, so a collaborator edit would leak across trips.
OWNER_ONLY_LOCATION_FIELDS = (
    'name', 'description', 'category', 'is_public', 'location',
    'latitude', 'longitude', 'coordinates',
)

ASPECT_PARAMETER = OpenApiParameter(
    'aspect', str, OpenApiParameter.PATH, enum=['square', 'story', 'landscape'],
    description='`square` (1080×1080), `story` (1080×1920) or `landscape` (1200×630).',
)
COLLECTION_ID_PARAMETER = OpenApiParameter(
    'collection_id', str, OpenApiParameter.PATH, description='The collection id.',
)
PNG_RESPONSE = {(200, 'image/png'): OpenApiResponse(response=bytes, description='A PNG image.')}


@extend_schema_view(
    retrieve=extend_schema(
        description='Anyone can read a public location. Otherwise you need to own it or be a member of a '
        'collection it is in.',
    ),
    create=extend_schema(
        description='Send `collections` (ids) to add it to collections you can edit. A place created in a '
        "collection belongs to the collection's owner.",
    ),
    update=extend_schema(
        description='Collaborators change visits, photos and collection links; `name`, `description`, '
        '`category`, `is_public`, `location` and the coordinates are kept as the owner set them.',
    ),
    partial_update=extend_schema(
        description='Like PUT, for the fields you send. Sending `collections` changes only links to '
        'collections you can open; links to others stay.',
    ),
    destroy=extend_schema(description='Only the owner can delete a location.'),
)
class LocationViewSet(ConditionalWritesMixin, ClientIdsMixin, PaginatedResponseMixin, viewsets.ModelViewSet):
    """
    Locations: places you have been or want to go, with visits, photos, files, trails and activities.

    A location belongs to one user. It can be in any number of collections; members of those
    collections can see it and editors can change some of it.
    """

    openapi_tags = ['Locations']
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess]
    pagination_class = pagination.StandardResultsSetPagination

    # Actions a signed-out visitor may use on a public location.
    PUBLIC_ACTIONS = {'retrieve', 'share_image', 'sun_times'}
    # Actions about the requester's own places, which need an account.
    OWN_PLACES_ACTIONS = {'list', 'pins', 'suggest', 'check_duplicates'}
    # Copying reads the original and writes only to the requester's account, so it needs an
    # account and read access to the place (checked in the action), not write access to it.
    COPY_ACTIONS = {'duplicate'}

    def get_permissions(self):
        if self.action in self.OWN_PLACES_ACTIONS or self.action in self.COPY_ACTIONS:
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Location.objects.none()
        user = self.request.user
        include_public = self.action in self.PUBLIC_ACTIONS or (
            user.is_authenticated and self.action in self.COPY_ACTIONS
        )
        if not user.is_authenticated:
            if include_public and can_read_published(user):
                return self._load_detail(
                    Location.objects.retrieve_locations(user, include_public=True).order_by('-updated_at')
                )
            return Location.objects.none()
        return self._load_detail(
            Location.objects.retrieve_locations(
                user, include_public=include_public, include_owned=True, include_shared=True
            ).order_by('-updated_at')
        )

    def _load_detail(self, queryset):
        """Fetch the images, attachments, trails, visits and owners a detail page shows in a few
        queries instead of one set per related row. Only for reads: after a write the serializer
        must see fresh rows, not what was prefetched."""
        if self.action == 'retrieve':
            return optimize_locations(queryset)
        return queryset

    # ==================== LIST ====================

    @extend_schema(parameters=[LocationListQuerySerializer], responses=LocationListSerializer(many=True))
    def list(self, request, *args, **kwargs):
        """
        List your locations

        The places you own and the ones you travelled to in a collection you belong to, a page
        at a time, in a light form (no trails, files or GPS tracks). Filter by category,
        visited status and whether they are in a collection. A place counts as visited when you
        were a traveler on a visit that has started.
        """
        params = validated(LocationListQuerySerializer, request.query_params)
        queryset = (
            Location.objects.filter(where_ive_been_q(request.user))
            .distinct()
            .annotate(annotated_is_visited=visited_by(request.user, timezone.now()))
            .select_related('category', 'user')
            .prefetch_related(Prefetch('images', queryset=ContentImage.objects.select_related('user')), 'collections')
        )
        if params.get('category'):
            names = [name.strip() for name in params['category'].split(',') if name.strip()]
            # Someone else's category is matched by name; your own only when it is yours.
            queryset = queryset.filter(
                Q(category__name__in=names) & (Q(category__user=request.user) | ~Q(user=request.user))
            )
        if params['is_visited'] is not None:
            queryset = queryset.filter(annotated_is_visited=params['is_visited'])
        if params['in_collection'] is not None:
            queryset = queryset.filter(collections__isnull=not params['in_collection'])
        # Visited/planned totals for the whole filtered set (not just this page): one aggregate
        # over the same filters as `count`, run before ordering and prefetching are applied.
        totals = queryset.order_by().aggregate(
            visited=Count('pk', distinct=True, filter=Q(annotated_is_visited=True)),
            total=Count('pk', distinct=True),
        )
        queryset = self._order(queryset.distinct(), params['ordering'])
        response = self.paginate_and_respond(queryset, request, serializer_class=LocationListSerializer)
        if isinstance(response.data, dict):
            response.data['visited_count'] = totals['visited']
            response.data['planned_count'] = totals['total'] - totals['visited']
        return response

    @staticmethod
    def _order(queryset, ordering):
        descending = ordering.startswith('-')
        field = ordering.lstrip('-')
        if field == 'name':
            queryset, expression = queryset.annotate(lower_name=Lower('name')), F('lower_name')
        elif field == 'date':
            queryset, expression = queryset.annotate(latest_visit=Max('visits__start_date')), F('latest_visit')
        else:
            expression = F(field)
        ordered = expression.desc(nulls_last=True) if descending else expression.asc(nulls_last=True)
        return queryset.order_by(ordered, 'id')

    # ==================== CRUD ====================

    @transaction.atomic
    def perform_create(self, serializer):
        collections = serializer.validated_data.get('collections', [])
        ensure_can_add_to_collections(self.request, collections, 'location')
        # A place created inside a collection belongs to the collection owner,
        # including when a collaborator creates it. Their own map does not gain the pin.
        serializer.save(
            user=collections[0].user if collections else self.request.user,
            created_by=self.request.user,
        )

    def update(self, request, *args, **kwargs):
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
            serializer.validated_data['collections'] = requested + [c for c in hidden if c not in requested]
            removed_collections = self._validate_collection_update_permissions(
                instance, serializer.validated_data['collections']
            )

        with transaction.atomic():
            serializer.save()
            for collection in removed_collections:
                unlink_location(instance, collection)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user and not creator_may_delete(instance, request.user):
            raise PermissionDenied('Only the owner can delete this location.')
        return super().destroy(request, *args, **kwargs)

    # ==================== CREATING AND COPYING ====================

    @extend_schema(request=QuickAddSerializer, responses={201: LocationQuickAddResultSerializer})
    @action(detail=False, methods=['post'], url_path='quick-add', throttle_classes=[ExternalGeocodeThrottle])
    def quick_add(self, request):
        """
        Add a location from a map pin

        Creates a location from a place picked on the map or from search, in one call: finds
        the country, region and city, picks or creates the category, optionally adds it to a
        collection and a trip day, and imports a few photos. Everything is undone if any
        step fails.
        """
        payload = request.data if isinstance(request.data, dict) else {}
        # Anything that fails inside rolls the whole thing back, so a refusal leaves no half-made place.
        with transaction.atomic():
            prepared = prepare_location_quick_add(
                request.user,
                payload,
                can_add_to_collection=lambda collection: can_edit(request, collection),
                language=resolve_request_language(request),
            )
            serializer = self.get_serializer(data=prepared.serializer_payload)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

            location = serializer.instance
            apply_reverse_geocode_result(location, prepared.reverse_data, prepared.location_label)
            itinerary_item, image_import_summary = finish_quick_add(location, prepared, payload)

        response_data = add_quick_add_extras(self.get_serializer(location).data, itinerary_item, image_import_summary)
        return Response(response_data, status=status.HTTP_201_CREATED)

    @extend_schema(request=DuplicateCheckSerializer, responses=DuplicateCheckResultSerializer)
    @action(detail=False, methods=['post'], url_path='check-duplicates')
    def check_duplicates(self, request):
        """
        Find likely duplicates

        Your existing locations that are probably the same place as one being added, by name
        and distance, best match first.
        """
        params = validated(DuplicateCheckSerializer, request.data)
        matches = find_duplicate_locations(
            request.user,
            name=params['name'].strip(),
            latitude=params.get('latitude'),
            longitude=params.get('longitude'),
            location=params.get('location'),
            exclude_id=params.get('exclude_id'),
        )
        return Response({'matches': [match.to_dict() for match in matches]})

    @extend_schema(parameters=[TravelerCandidatesQuerySerializer], responses=TravelerSerializer(many=True))
    @action(detail=True, methods=['get'], url_path='traveler-candidates')
    def traveler_candidates(self, request, pk=None):
        """
        List who can be a traveler

        The people a visit here can name as travelers, as you see them: the location's owner, plus
        the owner and members of the collections holding it that you own or belong to (the
        location's owner gets those of every collection holding it). With `collection`, only that
        trip's people and the location owner.
        """
        location = self.get_object()
        if not can_read_location(request, location):
            raise NotFound('Location not found.')
        params = validated(TravelerCandidatesQuerySerializer, request.query_params)
        if params.get('collection'):
            collection = Collection.objects.filter(pk=params['collection'], locations=location).first()
            if collection is None or not is_member(request.user, collection):
                raise NotFound('Collection not found.')
            people = candidates(location, collection=collection)
        else:
            people = candidates(location, request.user)
        return Response(TravelerSerializer(people, many=True, context={'request': request}).data)

    @extend_schema(
        request=LocationDuplicateRequestSerializer,
        responses={
            201: LocationSerializer,
            413: OpenApiResponse(
                response=ErrorSerializer,
                description="The copy's photos would take you over your media storage limit (`media_quota_exceeded`). "
                'Never for `take_my_visits`.'
            ),
        },
    )
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """
        Copy a location

        Copies a place you can see into your own account, with its photos but not its visits,
        attachments or trails. The copy shares the original's stored photo files. A copy of
        someone else's place leaves out photos linked from their Immich library. Optionally puts
        the copy in a collection. With `take_my_visits`, for a location you travelled to but
        don't own (say, before leaving its trip), the copy keeps the original name, your visits
        move onto it, and you are taken off the original's visits.

        A copy you choose to make counts toward your media storage limit: photo files you don't
        already hold are counted once, and over the limit the copy is refused. `take_my_visits`
        is keeping your own history, so it is never refused.
        """
        original = self.get_object()
        if not can_read_location(request, original):
            raise PermissionDenied('You do not have permission to copy this location.')

        collection = None
        params = validated(LocationDuplicateRequestSerializer, request.data)
        collection_id = params.get('collection')
        if collection_id:
            collection = Collection.objects.filter(id=collection_id).first()
            if collection is None:
                raise NotFound('Collection not found.')
            if not can_edit(request, collection):
                raise PermissionDenied('You do not have permission to add locations to this collection.')

        if not params['take_my_visits']:
            ensure_room_for_names(request.user, shared_file_names(original))
        try:
            if params['take_my_visits']:
                new_location = take_my_visits(original, request.user, collection=collection)
            else:
                new_location = copy_location(original, request.user, collection)
        except (APIException, ServiceError):
            raise
        except Exception:
            logger.exception('Failed to duplicate location %s', pk)
            raise APIError('The location could not be copied.', code='server_error', status=500)
        return Response(self.get_serializer(new_location).data, status=status.HTTP_201_CREATED)

    # ==================== OTHER VIEWS OF A LOCATION ====================

    @extend_schema(parameters=[ASPECT_PARAMETER, ShareImageQuerySerializer], responses=PNG_RESPONSE)
    @action(detail=True, methods=['get'], url_path=r'share-image/(?P<aspect>square|story|landscape)')
    def share_image(self, request, pk=None, aspect=None):
        """
        Get a share card

        A branded PNG for social media with the place's photo, name and a link. Public places
        can be fetched without signing in.
        """
        params = validated(ShareImageQuerySerializer, request.query_params)
        location = self.get_object()
        try:
            location = get_location_for_share(location.id)
            png_bytes = build_share_image(location, aspect, resolve_share_page_url(request, f'/locations/{location.id}'))
        except Exception:
            logger.exception('Failed to generate share image for location %s', location.id)
            raise APIError('The share image could not be made. Please try again later.', code='server_error', status=500)

        response = HttpResponse(png_bytes, content_type='image/png')
        disposition = 'attachment' if params['download'] else 'inline'
        response['Content-Disposition'] = f'{disposition}; filename="{share_image_filename(location, aspect)}"'
        return response

    @extend_schema(
        parameters=[SunTimesQuerySerializer],
        responses={200: SunTimesSerializer, 404: OpenApiResponse(description='No times for this place or date.')},
    )
    @action(detail=True, methods=['get'], url_path='sun-times', throttle_classes=[ExternalSunriseSunsetThrottle])
    def sun_times(self, request, pk=None):
        """
        Get sunrise and sunset

        Sunrise and sunset at the place on a date, in its local time. Needs coordinates.
        """
        params = validated(SunTimesQuerySerializer, request.query_params)
        # Guest links can read places in their collection, which the detail queryset leaves out.
        location = Location.objects.filter(pk=as_uuid(pk)).first() if as_uuid(pk) else None
        if location is None or not can_read_location(request, location):
            raise NotFound('Location not found.')
        if not location.coordinates:
            raise APIError('This location has no coordinates.', code='no_coordinates')
        latitude, longitude = point_to_lat_lon(location.coordinates)
        times = get_sunrise_sunset_for_date(latitude, longitude, params['date'].isoformat())
        if not times:
            raise NotFound('Sunrise and sunset are not available for this date.')
        return Response(times)

    @extend_schema(responses=MapPinSerializer(many=True))
    @action(detail=False, methods=['get'], url_path='pins', pagination_class=None)
    def pins(self, request):
        """
        List map pins

        Every location you own or travelled to in a collection you belong to, with just what a
        map needs: name, coordinates, category and whether you have visited it.
        """
        locations = (
            Location.objects.filter(where_ive_been_q(request.user))
            .distinct()
            .select_related('category__user', 'user')
            .prefetch_related('visits__travelers', 'collections__shared_with')
        )
        return Response(MapPinSerializer(locations, many=True, context={'request': request}).data)

    @extend_schema(parameters=[LocationSuggestQuerySerializer], responses=LocationSuggestResponseSerializer)
    @action(detail=False, methods=['get'], url_path='suggest', pagination_class=None)
    def suggest(self, request):
        """
        Suggest your locations

        Your own places for adding to a collection, a page at a time. With `q`, search by name.
        With `collection`, places closest to the middle of that collection come first;
        otherwise A to Z.
        """
        params = validated(LocationSuggestQuerySerializer, request.query_params)
        center = None
        if params.get('collection'):
            collection = Collection.objects.filter(id=params['collection']).first()
            if collection is None or not is_member(request, collection):
                raise NotFound('Collection not found.')
            center = collection_center(collection)

        # MapPinSerializer reads each place's visits and travelers (perspective_user, is_visited).
        locations = (
            Location.objects.filter(user=request.user).select_related('category__user', 'user')
            .prefetch_related('visits__travelers', 'collections__shared_with')
        )
        query = params['q'].strip()
        if len(query) >= 2:
            locations = locations.filter(name__icontains=query)
        count = locations.count()
        if center is not None:
            locations = locations.annotate(distance=Distance('coordinates', center)).order_by(
                F('distance').asc(nulls_last=True), 'name'
            )
        else:
            locations = locations.order_by('name')

        offset, limit = params['offset'], params['limit']
        return Response({
            'count': count,
            'results': MapPinSerializer(locations[offset:offset + limit], many=True, context={'request': request}).data,
            'anchored': center is not None,
        })

    # ==================== COLLECTION MEMBERSHIP ====================

    def _location_owner_fits(self, location, collection):
        """The place owner must own the collection or be a member of it."""
        return (
            collection.user_id == location.user_id
            or collection.shared_with.filter(id=location.user_id).exists()
        )

    @extend_schema(
        parameters=[CollectionMembershipQuerySerializer], responses=CollectionMembershipSerializer(many=True)
    )
    @action(detail=True, methods=['get'], url_path='collections', pagination_class=None)
    def collection_memberships(self, request, pk=None):
        """
        List the location's collections

        The collections the place is in, then the ones you could add it to, with what you are
        allowed to do in each.
        """
        location = self.get_object()
        query = validated(CollectionMembershipQuerySerializer, request.query_params)['q'].strip()

        linked_ids = set(location.collections.values_list('pk', flat=True))
        candidates = Collection.objects.filter(
            Q(pk__in=linked_ids) & readable_collections_q(request)
            | member_collections_q(request, editable=True)
        ).distinct().select_related('user')
        if query:
            candidates = candidates.filter(name__icontains=query)

        rows = []
        for collection in candidates:
            is_linked = collection.pk in linked_ids
            editable = can_edit(request, collection)
            rows.append({
                'id': str(collection.pk),
                'name': collection.name,
                'start_date': collection.start_date,
                'end_date': collection.end_date,
                'is_shared': collection.user_id != request.user.id,
                'owner_name': collection.user.username,
                'role': member_role(collection, request.user),
                'is_linked': is_linked,
                'can_link': editable and self._location_owner_fits(location, collection),
                'can_unlink': self._may_unlink(request, location, collection),
                'placements': placements_for(location, collection) if is_linked else [],
            })
        rows.sort(key=lambda r: (not r['is_linked'], r['is_shared'], (r['name'] or '').lower()))
        return Response(rows)

    @extend_schema(
        methods=['POST'], request=None, responses=CollectionLinkResultSerializer,
        summary='Add the location to a collection',
        description='Idempotent. The place owner must own the collection or be a member of it.',
        parameters=[COLLECTION_ID_PARAMETER],
    )
    @extend_schema(
        methods=['DELETE'], request=None,
        responses={200: CollectionLinkResultSerializer},
        summary='Remove the location from a collection',
        description='Idempotent. Also removes its placements from the day plan, and says how many. '
                    'Only the collection owner, the place owner, or the person who added the place (while an '
                    'editor) may call it. People who travelled to the place and can no longer reach it through '
                    'another collection come off its visits and get their own copy with their visits. '
                    '`GET …/collections/{collection_id}/unlink-preview/` says who that would be.',
        parameters=[COLLECTION_ID_PARAMETER],
    )
    @action(detail=True, methods=['post', 'delete'], url_path=r'collections/(?P<collection_id>[^/.]+)')
    def collection_membership(self, request, pk=None, collection_id=None):
        location = self.get_object()
        collection = self._readable_collection(request, collection_id)

        if request.method == 'POST':
            if not can_edit(request, collection):
                raise PermissionDenied("You don't have permission to add locations to this collection.")
            if not self._location_owner_fits(location, collection):
                raise APIError('The location owner must own or be a member of this collection.', code='invalid')
            link_location(location, collection)
            return Response({'linked': True})

        self._check_may_unlink(request, location, collection)
        removed = unlink_location(location, collection)
        return Response({'linked': False, 'removed_placements': removed})

    @extend_schema(responses=UnlinkPreviewSerializer, parameters=[COLLECTION_ID_PARAMETER])
    @action(
        detail=True, methods=['get'], url_path=r'collections/(?P<collection_id>[^/.]+)/unlink-preview',
        throttle_classes=[SharingPreviewThrottle],
    )
    def unlink_preview(self, request, pk=None, collection_id=None):
        """
        Preview removing the location from a collection

        What `DELETE /api/locations/{id}/collections/{collection_id}/` would do, changing nothing:
        who would get their own copy (`people_released`), the visits and uploads that would go with
        the original, and the plan placements removed. The same people may ask as may remove it.
        """
        refuse_anonymous_preview(request, guest_reaches_lookup=True)
        location = self.get_object()
        collection = self._readable_collection(request, collection_id)
        self._check_may_unlink(request, location, collection)
        summary = release_summary(lost_access_plan([location], ignoring=[collection]), request.user)
        summary['removed_placements'] = len(placements_for(location, collection))
        return preview_response(UnlinkPreviewSerializer(summary, context={'request': request}).data)

    # ==================== HELPERS ====================

    @staticmethod
    def _readable_collection(request, collection_id):
        """The collection ``collection_id`` names, when the requester can read it; 404 otherwise."""
        collection = Collection.objects.filter(pk=collection_id).filter(readable_collections_q(request)).first() \
            if as_uuid(collection_id) else None
        if collection is None:
            raise NotFound('Collection not found.')
        return collection

    def _check_may_unlink(self, request, location, collection):
        if not self._may_unlink(request, location, collection):
            raise PermissionDenied(
                'Only the collection owner, the place owner, or the person who added it can remove a place '
                'from a collection. '
                'You can remove it from the plan instead.'
            )

    @staticmethod
    def _may_unlink(request, location, collection):
        """
        The collection owner, the place owner, or whoever added the place may take it out of a
        collection. The one who added it must still be an editor of that collection.
        """
        if request.user.id in (collection.user_id, location.user_id):
            return True
        return (
            location.created_by_id is not None
            and location.created_by_id == request.user.id
            and member_role(collection, request.user) == EDITOR
        )

    def _validate_collection_update_permissions(self, instance, new_collections):
        """Check collection permissions for an update. Returns the collections being removed."""
        current_collections = set(instance.collections.all())
        new_collections_set = set(new_collections)

        for collection in new_collections_set - current_collections:
            if not can_edit(self.request, collection):
                raise PermissionDenied(f"You don't have permission to add location to collection '{collection.name}'")

        # A collection can be removed by the place owner or the collection owner only.
        collections_to_remove = current_collections - new_collections_set
        for collection in collections_to_remove:
            if not self._may_unlink(self.request, instance, collection):
                raise PermissionDenied(
                    "You don't have permission to remove this location from one of the collections it's linked to."
                )
        return list(collections_to_remove)

