from datetime import date, datetime, timezone as dt_timezone
from django.db.models import Count, Q, Prefetch
from django.db.models.functions import Lower
from django.db import transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from django.utils import timezone
from rest_framework.parsers import MultiPartParser
from rest_framework import status
from django.http import HttpResponse
from django.conf import settings
from django.core.files.base import ContentFile
import io
import os
import json
import zipfile
import tempfile
import logging
from adventures.models import CollectionActivity, CollectionGuestLink, CollectionMember
from adventures.utils.activity import record_activity
from adventures.models import Collection, Location, Transportation, Note, Checklist, ChecklistItem, CollectionInvite, ContentImage, CollectionItineraryItem, Lodging, CollectionItineraryDay, ContentAttachment, Category
from adventures.permissions import CollectionShared
from adventures.utils.audience import audience_for_request, readable_collections_q
from adventures.utils.query_optimization import media_prefetches, optimize_locations
from adventures.utils.story import build_story_payload
from adventures.serializers import _build_profile_pic_url
from adventures.serializers import CollectionSerializer, CollectionInviteSerializer, UltraSlimCollectionSerializer, CollectionItineraryItemSerializer, CollectionItineraryDaySerializer
from users.models import CustomUser as User
from adventures.utils import pagination
from adventures.utils import itinerary_days as day_plan
from adventures.utils.timezones import timezone_or_utc
from adventures.utils.geo import make_point, point_to_lat_lon
from adventures.utils.collection_type import (
    BACKUP_SCHEMA,
    UnsupportedBackupSchema,
    resolve_imported_collection_type,
)
from adventures.services.locations.duplicates import find_best_duplicate_location
from adventures.services.collection_pdf import (
    build_collection_pdf,
    get_collection_for_pdf,
    pdf_filename_for_collection,
)
from adventures.services.share_image import (
    build_share_image,
    get_collection_for_share,
    resolve_share_page_url,
    share_image_filename,
    valid_aspect,
)

logger = logging.getLogger(__name__)


def _iso(value):
    return value.isoformat() if value else None


def _export_lat_lon(point):
    lat, lon = point_to_lat_lon(point)
    return (
        float(lat) if lat is not None else None,
        float(lon) if lon is not None else None,
    )


def _money_amount(money):
    return str(money.amount) if money else None


def _money_currency(money):
    return str(money.currency) if money else None


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _parse_money(amount, currency=None, default_currency='USD'):
    if amount in (None, ''):
        return None, default_currency
    normalized = currency or default_currency
    if isinstance(normalized, str):
        normalized = normalized.strip().upper() or default_currency
    else:
        normalized = default_currency
    return amount, normalized


def _parse_role(value):
    value = (value or CollectionMember.Role.EDITOR)
    return value if value in CollectionMember.Role.values else None


def _sharing_state(collection, request):
    """What the owner's Share sheet shows."""
    roles = {
        user_id: role
        for user_id, role in CollectionMember.objects.filter(collection=collection).values_list('user_id', 'role')
    }
    members = []
    for user in collection.shared_with.all().order_by('username'):
        members.append({
            'uuid': str(user.uuid),
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'profile_pic': _build_profile_pic_url(user),
            'role': roles.get(user.id, CollectionMember.Role.EDITOR),
        })
    invites = [
        {
            'uuid': str(invite.invited_user.uuid),
            'username': invite.invited_user.username,
            'first_name': invite.invited_user.first_name,
            'last_name': invite.invited_user.last_name,
            'role': invite.role,
        }
        for invite in CollectionInvite.objects.filter(collection=collection).select_related('invited_user')
    ]
    guest_links = [
        {
            'id': str(link.id),
            'token': link.token,
            'role': link.role,
            'label': link.label,
            'expires_at': link.expires_at,
            'revoked_at': link.revoked_at,
            'created_at': link.created_at,
            'is_active': link.is_active,
        }
        for link in collection.guest_links.all()
    ]
    return {
        'owner': {
            'uuid': str(collection.user.uuid),
            'username': collection.user.username,
            'first_name': collection.user.first_name,
            'last_name': collection.user.last_name,
        },
        'members': members,
        'invites': invites,
        'guest_links': guest_links,
        'visibility': collection.visibility,
        'story_groups': {name: collection.story_group(name) for name in Collection.STORY_GROUPS},
        'comment_access': collection.comment_access,
        'share_secret': collection.share_secret,
        'allow_public_links': settings.ALLOW_PUBLIC_COLLECTION_LINKS,
        # Admins see how to turn public links on; everyone else is told to ask one.
        'is_admin': bool(getattr(request.user, 'is_staff', False)),
    }


class CollectionViewSet(viewsets.ModelViewSet):
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

        # Apply case-insensitive sorting for the 'name' field
        if order_by == 'name':
            queryset = queryset.annotate(lower_name=Lower('name'))
            ordering = 'lower_name'
            if order_direction == 'asc':
                ordering = f'-{ordering}'
        elif order_by == 'start_date':
            ordering = 'start_date'
            if order_direction == 'desc':
                ordering = 'start_date'
            else:
                ordering = '-start_date'
        else:
            order_by == 'updated_at'
            ordering = 'updated_at'
            if order_direction == 'desc':
                ordering = '-updated_at'

        return queryset.order_by(ordering)
    
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
        ).distinct().select_related('user', 'primary_image').prefetch_related(
            Prefetch(
                'locations__images',
                queryset=ContentImage.objects.filter(is_primary=True).select_related('user'),
                to_attr='primary_images'
            )
        )
        
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
        ).select_related('user', 'primary_image').prefetch_related(
            Prefetch(
                'locations__images',
                queryset=ContentImage.objects.filter(is_primary=True).select_related('user'),
                to_attr='primary_images'
            )
        )
        
        queryset = self.apply_sorting(self._for_listing(queryset))
        serializer = self.get_serializer(queryset, many=True)
       
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def archived(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
       
        queryset = Collection.objects.filter(
            Q(user=request.user.id) & Q(is_archived=True)
        ).select_related('user', 'primary_image').prefetch_related(
            Prefetch(
                'locations__images',
                queryset=ContentImage.objects.filter(is_primary=True).select_related('user'),
                to_attr='primary_images'
            )
        )
        
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
        from adventures.utils.day_files import serialize_day_files

        data.update(serialize_day_files(collection, context))

        if story_mode:
            story = build_story_payload(data, collection)
            story['audience'] = audience.as_dict()
            story['story_preview'] = not audience.is_public_reader
            return Response(story)
        return Response(data)
    
    # make an action to retreive all locations that are shared with the user
    @action(detail=False, methods=['get'])
    def shared(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        
        queryset = Collection.objects.filter(
            shared_with=request.user
        ).select_related('user').prefetch_related(
            Prefetch(
                'locations__images',
                queryset=ContentImage.objects.filter(is_primary=True).select_related('user'),
                to_attr='primary_images'
            )
        )
        
        queryset = self.apply_sorting(self._for_listing(queryset))
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    # Created a custom action to share a collection with another user by their UUID
    # This action will create a CollectionInvite instead of directly sharing the collection
    @action(detail=True, methods=['post'], url_path='share/(?P<uuid>[^/.]+)')
    def share(self, request, pk=None, uuid=None):
        collection = self.get_object()
        if not uuid:
            return Response({"error": "User UUID is required"}, status=400)
        try:
            user = User.objects.get(uuid=uuid, public_profile=True)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        
        if user == request.user:
            return Response({"error": "Cannot share with yourself"}, status=400)
        
        # Check if user is already shared with the collection
        if collection.shared_with.filter(id=user.id).exists():
            return Response({"error": "Collection is already shared with this user"}, status=400)
        
        # Check if there's already a pending invite for this user
        if CollectionInvite.objects.filter(collection=collection, invited_user=user).exists():
            return Response({"error": "Invite already sent to this user"}, status=400)
        
        role = _parse_role(request.data.get('role'))
        if role is None:
            return Response({"error": "Role must be editor or viewer"}, status=400)

        # Create the invite instead of directly sharing
        invite = CollectionInvite.objects.create(
            collection=collection,
            invited_user=user,
            role=role,
        )
        
        return Response({"success": f"Invite sent to {user.username}"})
    
    # Custom action to list all invites for a user
    @action(detail=False, methods=['get'], url_path='invites')
    def invites(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        
        invites = CollectionInvite.objects.filter(invited_user=request.user)
        serializer = CollectionInviteSerializer(invites, many=True)
        
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='revoke-invite/(?P<uuid>[^/.]+)')
    def revoke_invite(self, request, pk=None, uuid=None):
        """Revoke a pending invite for a collection"""
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        
        collection = self.get_object()
        
        if not uuid:
            return Response({"error": "User UUID is required"}, status=400)
        
        try:
            user = User.objects.get(uuid=uuid)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        
        # Only collection owner can revoke invites
        if collection.user != request.user:
            return Response({"error": "Only collection owner can revoke invites"}, status=403)
        
        try:
            invite = CollectionInvite.objects.get(collection=collection, invited_user=user)
            invite.delete()
            return Response({"success": f"Invite revoked for {user.username}"})
        except CollectionInvite.DoesNotExist:
            return Response({"error": "No pending invite found for this user"}, status=404)

    @action(detail=True, methods=['post'], url_path='accept-invite')
    def accept_invite(self, request, pk=None):
        """Accept a collection invite"""
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        
        collection = self.get_object()
        
        try:
            invite = CollectionInvite.objects.get(collection=collection, invited_user=request.user)
        except CollectionInvite.DoesNotExist:
            return Response({"error": "No pending invite found for this collection"}, status=404)
        
        # Add user to collection's shared_with with the invited role
        collection.shared_with.add(request.user)
        CollectionMember.objects.update_or_create(
            collection=collection, user=request.user, defaults={'role': invite.role}
        )
        record_activity(
            collection, request, CollectionActivity.Verb.MEMBER_ADDED,
            username=request.user.username, role=invite.role,
        )
        
        # Delete the invite
        invite.delete()
        
        return Response({"success": f"Successfully joined collection: {collection.name}"})

    @action(detail=True, methods=['post'], url_path='decline-invite')
    def decline_invite(self, request, pk=None):
        """Decline a collection invite"""
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        
        collection = self.get_object()
        
        try:
            invite = CollectionInvite.objects.get(collection=collection, invited_user=request.user)
            invite.delete()
            return Response({"success": f"Declined invite for collection: {collection.name}"})
        except CollectionInvite.DoesNotExist:
            return Response({"error": "No pending invite found for this collection"}, status=404)
    
    # Action to list all users a collection **can** be shared with, excluding those already shared with and those with pending invites
    @action(detail=True, methods=['get'], url_path='can-share')
    def can_share(self, request, pk=None):
        """
        People the owner can invite: public profiles that are not the owner, a
        member, or already invited. Search with ``q`` (name or username, at
        least 2 characters). At most ``limit`` rows (default 20, max 50), so
        the Share sheet stays fast on servers with thousands of users.
        """
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        
        collection = self.get_object()

        query = (request.query_params.get('q') or '').strip()
        try:
            limit = max(1, min(int(request.query_params.get('limit', 20)), 50))
        except (TypeError, ValueError):
            limit = 20

        candidates = (
            User.objects.filter(public_profile=True)
            .exclude(id=collection.user_id)
            .exclude(id__in=collection.shared_with.values('id'))
            .exclude(id__in=CollectionInvite.objects.filter(collection=collection).values('invited_user_id'))
        )
        if query:
            if len(query) < 2:
                return Response([])
            terms = Q()
            for word in query.split()[:3]:
                terms &= (
                    Q(username__icontains=word)
                    | Q(first_name__icontains=word)
                    | Q(last_name__icontains=word)
                )
            candidates = candidates.filter(terms)

        users = candidates.order_by('username').only(
            'uuid', 'username', 'first_name', 'last_name', 'profile_pic'
        )[:limit]
        return Response([
            {
                'uuid': str(user.uuid),
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'profile_pic': _build_profile_pic_url(user),
                'status': 'available',
            }
            for user in users
        ])

    @action(detail=True, methods=['post'], url_path='unshare/(?P<uuid>[^/.]+)')
    def unshare(self, request, pk=None, uuid=None):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        
        collection = self.get_object()
        
        if not uuid:
            return Response({"error": "User UUID is required"}, status=400)
        
        try:
            user = User.objects.get(uuid=uuid)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        
        if user == request.user:
            return Response({"error": "Cannot unshare with yourself"}, status=400)
        
        if not collection.shared_with.filter(id=user.id).exists():
            return Response({"error": "Collection is not shared with this user"}, status=400)
        
        # Remove user from shared_with. Places created in the collection belong to its
        # owner and stay. A place the member already owned stays theirs and stays linked.
        collection.shared_with.remove(user)
        collection.save()
        record_activity(collection, request, CollectionActivity.Verb.MEMBER_REMOVED, username=user.username)
        
        return Response({"success": f"Unshared with {user.username}"})
    
    # Action for a shared user to leave a collection
    @action(detail=True, methods=['post'], url_path='leave')
    def leave(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        
        collection = self.get_object()
        
        if request.user == collection.user:
            return Response({"error": "Owner cannot leave their own collection"}, status=400)
        
        if not collection.shared_with.filter(id=request.user.id).exists():
            return Response({"error": "You are not a member of this collection"}, status=400)
        
        # Remove the user from shared_with. Their own places stay theirs and stay linked.
        collection.shared_with.remove(request.user)
        collection.save()
        record_activity(
            collection, request, CollectionActivity.Verb.MEMBER_REMOVED, username=request.user.username, left=True
        )
        
        return Response({"success": f"You have left the collection: {collection.name}"})

    # -- Sharing (owner only) -------------------------------------------------

    def _owned_collection(self, request, pk):
        collection = Collection.objects.filter(pk=pk, user=request.user.id).first()
        if collection is None:
            raise NotFound('Collection not found.')
        return collection

    @action(detail=True, methods=['get'], url_path='sharing')
    def sharing(self, request, pk=None):
        """Members with roles, pending invites, guest links, and story settings."""
        if not request.user.is_authenticated:
            raise NotFound('Collection not found.')
        collection = self._owned_collection(request, pk)
        return Response(_sharing_state(collection, request))

    @action(detail=True, methods=['post'], url_path='members/(?P<uuid>[^/.]+)/role')
    def member_role(self, request, pk=None, uuid=None):
        if not request.user.is_authenticated:
            raise NotFound('Collection not found.')
        collection = self._owned_collection(request, pk)
        role = _parse_role(request.data.get('role'))
        if role is None:
            return Response({"error": "Role must be editor or viewer"}, status=400)
        user = collection.shared_with.filter(uuid=uuid).first()
        if user is None:
            invite = CollectionInvite.objects.filter(collection=collection, invited_user__uuid=uuid).first()
            if invite is None:
                return Response({"error": "That person is not a member of this collection"}, status=404)
            invite.role = role
            invite.save(update_fields=['role', 'updated_at'])
        else:
            CollectionMember.objects.update_or_create(collection=collection, user=user, defaults={'role': role})
        return Response(_sharing_state(collection, request))

    @action(detail=True, methods=['post'], url_path='guest-links')
    def create_guest_link(self, request, pk=None):
        """Create a guest link with a role and an optional expiry. The owner can create several."""
        if not request.user.is_authenticated:
            raise NotFound('Collection not found.')
        collection = self._owned_collection(request, pk)
        role = _parse_role(request.data.get('role') or CollectionMember.Role.VIEWER)
        if role is None:
            return Response({"error": "Role must be editor or viewer"}, status=400)
        expires_at = None
        if request.data.get('expires_at'):
            expires_at = _parse_datetime(request.data.get('expires_at'))
            if expires_at is None:
                return Response({"error": "Use an ISO date and time for expires_at"}, status=400)
            if timezone.is_naive(expires_at):
                expires_at = timezone.make_aware(expires_at, dt_timezone.utc)
            if expires_at <= timezone.now():
                return Response({"error": "The expiry must be in the future"}, status=400)
        CollectionGuestLink.objects.create(
            collection=collection,
            role=role,
            label=(request.data.get('label') or '')[:100],
            expires_at=expires_at,
        )
        return Response(_sharing_state(collection, request), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='guest-links/(?P<link_id>[^/.]+)/revoke')
    def revoke_guest_link(self, request, pk=None, link_id=None):
        if not request.user.is_authenticated:
            raise NotFound('Collection not found.')
        collection = self._owned_collection(request, pk)
        link = CollectionGuestLink.objects.filter(collection=collection, pk=link_id).first()
        if link is None:
            return Response({"error": "Guest link not found"}, status=404)
        if link.revoked_at is None:
            link.revoked_at = timezone.now()
            link.save(update_fields=['revoked_at'])
        return Response(_sharing_state(collection, request))

    @action(detail=True, methods=['get'], url_path='export-pdf')
    def export_pdf(self, request, pk=None):
        """Export collection as a printable day-by-day itinerary PDF."""
        collection = self.get_object()
        audience = audience_for_request(request, collection)
        try:
            collection = get_collection_for_pdf(collection.id)
            # A public reader gets the story groups. Members get the full plan.
            pdf_bytes = build_collection_pdf(collection, story=audience.is_public_reader)
        except Exception:
            logger.exception('Failed to generate PDF for collection %s', collection.id)
            return Response(
                {'error': 'Failed to generate PDF. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        filename = pdf_filename_for_collection(collection)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(
        detail=True,
        methods=['get'],
        url_path=r'share-image/(?P<aspect>square|story|landscape)',
    )
    def share_image(self, request, pk=None, aspect=None):
        """Generate a branded PNG share card for social media."""
        if not valid_aspect(aspect):
            return Response({'error': 'Invalid aspect ratio.'}, status=status.HTTP_400_BAD_REQUEST)

        collection = self.get_object()
        try:
            collection = get_collection_for_share(collection.id)
            page_url = resolve_share_page_url(request, f'/collections/{collection.id}')
            png_bytes = build_share_image(collection, aspect, page_url)
        except Exception:
            logger.exception('Failed to generate share image for collection %s', collection.id)
            return Response(
                {'error': 'Failed to generate share image. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        filename = share_image_filename(collection, aspect)
        disposition = 'attachment' if request.query_params.get('download') else 'inline'
        response = HttpResponse(png_bytes, content_type='image/png')
        response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
        return response

    @action(detail=True, methods=['get'], url_path='export')
    def export_collection(self, request, pk=None):
        """Export a single collection and its related content as a ZIP file."""
        collection = self.get_object()

        export_data = {
            'version': getattr(settings, 'ADVENTURELOG_RELEASE_VERSION', 'unknown'),
            'backup_schema': BACKUP_SCHEMA,
            'collection': {
                'id': str(collection.id),
                'name': collection.name,
                'description': collection.description,
                'is_public': collection.is_public,
                'is_archived': collection.is_archived,
                'start_date': _iso(collection.start_date),
                'end_date': _iso(collection.end_date),
                'type': collection.type,
                'timezone': collection.timezone,
                'day_count': day_plan.day_count(collection) or None,
                'link': collection.link,
            },
            'locations': [],
            'transportation': [],
            'notes': [],
            'checklists': [],
            'lodging': [],
            # Omit itinerary_items entirely
            'images': [],
            'attachments': [],
            'primary_image_ref': None,
        }

        image_export_map = {}

        for loc in collection.locations.all().select_related('city', 'region', 'country', 'category'):
            loc_lat, loc_lon = _export_lat_lon(loc.coordinates)
            loc_entry = {
                'id': str(loc.id),
                'name': loc.name,
                'description': loc.description,
                'location': loc.location,
                'tags': loc.tags or [],
                'rating': loc.rating,
                'link': loc.link,
                'is_public': loc.is_public,
                'longitude': loc_lon,
                'latitude': loc_lat,
                'category': loc.category.name if loc.category else None,
                'city': loc.city.name if loc.city else None,
                'region': loc.region.name if loc.region else None,
                'country': loc.country.name if loc.country else None,
                'images': [],
                'attachments': [],
            }

            for img in loc.images.all():
                img_export_id = f"img_{len(export_data['images'])}"
                image_export_map[str(img.id)] = img_export_id
                export_data['images'].append({
                    'export_id': img_export_id,
                    'id': str(img.id),
                    'name': os.path.basename(getattr(img.image, 'name', 'image')),
                    'is_primary': getattr(img, 'is_primary', False),
                })
                loc_entry['images'].append(img_export_id)

            for att in loc.attachments.all():
                att_export_id = f"att_{len(export_data['attachments'])}"
                export_data['attachments'].append({
                    'export_id': att_export_id,
                    'id': str(att.id),
                    'name': os.path.basename(getattr(att.file, 'name', 'attachment')),
                })
                loc_entry['attachments'].append(att_export_id)

            export_data['locations'].append(loc_entry)

        if collection.primary_image:
            export_data['primary_image_ref'] = image_export_map.get(str(collection.primary_image.id))

        # Related content (if models have FK to collection)
        for t in Transportation.objects.filter(collection=collection):
            origin_lat, origin_lon = _export_lat_lon(t.origin)
            dest_lat, dest_lon = _export_lat_lon(t.destination)
            export_data['transportation'].append({
                'id': str(t.id),
                'type': t.type,
                'name': t.name,
                'description': t.description,
                'rating': t.rating,
                'price': _money_amount(t.price),
                'price_currency': _money_currency(t.price),
                'link': t.link,
                'date': _iso(t.date),
                'end_date': _iso(t.end_date),
                'start_timezone': t.start_timezone,
                'end_timezone': t.end_timezone,
                'flight_number': t.flight_number,
                'from_location': t.from_location,
                'to_location': t.to_location,
                'origin_latitude': origin_lat,
                'origin_longitude': origin_lon,
                'destination_latitude': dest_lat,
                'destination_longitude': dest_lon,
                'start_code': t.start_code,
                'end_code': t.end_code,
                'is_public': t.is_public,
            })
        for n in Note.objects.filter(collection=collection):
            export_data['notes'].append({
                'id': str(n.id),
                'name': n.name,
                'content': n.content or '',
                'links': n.links or [],
                'date': _iso(n.date),
                'is_public': n.is_public,
            })
        for c in Checklist.objects.filter(collection=collection):
            items = [
                {
                    'name': item.name,
                    'is_checked': item.is_checked,
                }
                for item in c.checklistitem_set.all()
            ]
            export_data['checklists'].append({
                'id': str(c.id),
                'name': c.name,
                'date': _iso(c.date),
                'is_public': c.is_public,
                'items': items,
            })
        for lodging in Lodging.objects.filter(collection=collection):
            lodging_lat, lodging_lon = _export_lat_lon(lodging.coordinates)
            export_data['lodging'].append({
                'id': str(lodging.id),
                'type': lodging.type,
                'name': lodging.name,
                'description': lodging.description,
                'rating': lodging.rating,
                'link': lodging.link,
                'check_in': _iso(lodging.check_in),
                'check_out': _iso(lodging.check_out),
                'timezone': lodging.timezone,
                'reservation_number': lodging.reservation_number,
                'price': _money_amount(lodging.price),
                'price_currency': _money_currency(lodging.price),
                'latitude': lodging_lat,
                'longitude': lodging_lon,
                'location': lodging.location,
                'is_public': lodging.is_public,
            })
        # Intentionally omit itinerary_items from export

        # Create ZIP in temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            with zipfile.ZipFile(tmp_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.writestr('metadata.json', json.dumps(export_data, indent=2))

                # Write image files
                for loc in collection.locations.all():
                    for img in loc.images.all():
                        export_id = image_export_map.get(str(img.id))
                        if not export_id:
                            continue
                        try:
                            file_name = os.path.basename(getattr(img.image, 'name', 'image'))
                            storage = getattr(img.image, 'storage', None)
                            if storage:
                                with storage.open(img.image.name, 'rb') as f:
                                    zipf.writestr(f'images/{export_id}-{file_name}', f.read())
                            elif hasattr(img.image, 'path'):
                                with open(img.image.path, 'rb') as f:
                                    zipf.writestr(f'images/{export_id}-{file_name}', f.read())
                        except Exception:
                            continue

                # Write attachment files
                for loc in collection.locations.all():
                    for att in loc.attachments.all():
                        try:
                            file_name = os.path.basename(getattr(att.file, 'name', 'attachment'))
                            storage = getattr(att.file, 'storage', None)
                            if storage:
                                with storage.open(att.file.name, 'rb') as f:
                                    zipf.writestr(f'attachments/{file_name}', f.read())
                            elif hasattr(att.file, 'path'):
                                with open(att.file.path, 'rb') as f:
                                    zipf.writestr(f'attachments/{file_name}', f.read())
                        except Exception:
                            continue

            with open(tmp_file.name, 'rb') as fh:
                data = fh.read()
            os.unlink(tmp_file.name)

        filename = f"collection-{collection.name.replace(' ', '_')}.zip"
        response = HttpResponse(data, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=['post'], url_path='import', parser_classes=[MultiPartParser])
    def import_collection(self, request):
        """Import a single collection from a ZIP file. Handles name conflicts by appending (n)."""
        upload = request.FILES.get('file')
        if not upload:
            return Response({'detail': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Read zip
        file_bytes = upload.read()
        with zipfile.ZipFile(io.BytesIO(file_bytes), 'r') as zipf:
            try:
                metadata = json.loads(zipf.read('metadata.json').decode('utf-8'))
            except KeyError:
                return Response({'detail': 'metadata.json missing'}, status=status.HTTP_400_BAD_REQUEST)

            base_name = (metadata.get('collection') or {}).get('name') or 'Imported Collection'

            # Ensure unique name per user
            existing_names = set(request.user.collection_set.values_list('name', flat=True))
            unique_name = base_name
            if unique_name in existing_names:
                i = 1
                while True:
                    candidate = f"{base_name} ({i})"
                    if candidate not in existing_names:
                        unique_name = candidate
                        break
                    i += 1

            collection_meta = metadata.get('collection') or {}
            try:
                imported_type = resolve_imported_collection_type(
                    metadata.get('backup_schema'),
                    collection_meta.get('start_date'),
                    collection_meta.get('end_date'),
                    collection_meta.get('type'),
                )
            except UnsupportedBackupSchema:
                return Response(
                    {'error': 'This backup uses a newer schema than this server supports.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except ValueError:
                return Response(
                    {'error': 'Invalid backup schema.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            new_collection = Collection.objects.create(
                user=request.user,
                name=unique_name,
                description=collection_meta.get('description'),
                is_public=collection_meta.get('is_public', False),
                is_archived=collection_meta.get('is_archived', False),
                start_date=_parse_date(collection_meta.get('start_date')),
                end_date=_parse_date(collection_meta.get('end_date')),
                type=imported_type,
                timezone=timezone_or_utc(collection_meta.get('timezone')),
                link=collection_meta.get('link'),
            )

            image_export_map = {img['export_id']: img for img in metadata.get('images', [])}
            attachment_export_map = {att['export_id']: att for att in metadata.get('attachments', [])}

            # Import locations
            for loc_data in metadata.get('locations', []):
                cat_obj = None
                if loc_data.get('category'):
                    cat_obj, _ = Category.objects.get_or_create(
                        user=request.user,
                        name=loc_data['category'],
                        defaults={'display_name': loc_data['category'], 'icon': '🌍'},
                    )
                incoming_name = loc_data.get('name') or 'Untitled'
                incoming_location_text = loc_data.get('location')
                incoming_lat = loc_data.get('latitude')
                incoming_lon = loc_data.get('longitude')

                existing_loc = find_best_duplicate_location(
                    request.user,
                    name=incoming_name,
                    latitude=incoming_lat,
                    longitude=incoming_lon,
                    location=incoming_location_text,
                )

                if existing_loc:
                    # Link existing location to the new collection, skip creating a duplicate
                    loc = existing_loc
                    loc.collections.add(new_collection)
                    created_new_loc = False
                else:
                    # Create a brand-new location
                    loc = Location(
                        user=request.user,
                        name=incoming_name,
                        description=loc_data.get('description'),
                        location=incoming_location_text,
                        tags=loc_data.get('tags') or [],
                        rating=loc_data.get('rating'),
                        link=loc_data.get('link'),
                        is_public=bool(loc_data.get('is_public', False)),
                        coordinates=make_point(incoming_lon, incoming_lat),
                        category=cat_obj,
                    )
                    loc.save(_skip_geocode=True)
                    loc.collections.add(new_collection)
                    created_new_loc = True

                # Images
                # Only import images for newly created locations to avoid duplicating user content
                if created_new_loc:
                    for export_id in loc_data.get('images', []):
                        img_meta = image_export_map.get(export_id)
                        if not img_meta:
                            continue
                        prefix = f"images/{export_id}-"
                        member = next((m for m in zipf.namelist() if m.startswith(prefix)), None)
                        if not member:
                            continue
                        file_bytes_img = zipf.read(member)
                        file_name_img = os.path.basename(member)
                        from django.core.files.base import ContentFile
                        image_obj = ContentImage(
                            user=request.user,
                            image=ContentFile(file_bytes_img, name=file_name_img),
                        )
                        # Assign to the generic relation for Location
                        image_obj.content_object = loc
                        image_obj.save()
                        if img_meta.get('is_primary'):
                            new_collection.primary_image = image_obj
                            new_collection.save(update_fields=['primary_image'])

                # Attachments
                if created_new_loc:
                    for export_id in loc_data.get('attachments', []):
                        att_meta = attachment_export_map.get(export_id)
                        if not att_meta:
                            continue
                        file_name_att = att_meta.get('name', '')
                        member = next((m for m in zipf.namelist() if m == f"attachments/{file_name_att}"), None)
                        if not member:
                            continue
                        file_bytes_att = zipf.read(member)
                        from django.core.files.base import ContentFile
                        attachment_obj = ContentAttachment(
                            user=request.user,
                            file=ContentFile(file_bytes_att, name=file_name_att),
                        )
                        # Assign to the generic relation for Location
                        attachment_obj.content_object = loc
                        attachment_obj.save()

            for trans_data in metadata.get('transportation', []):
                origin = make_point(
                    trans_data.get('origin_longitude'),
                    trans_data.get('origin_latitude'),
                )
                destination = make_point(
                    trans_data.get('destination_longitude'),
                    trans_data.get('destination_latitude'),
                )
                transport_price, transport_currency = _parse_money(
                    trans_data.get('price'),
                    trans_data.get('price_currency'),
                )
                Transportation.objects.create(
                    user=request.user,
                    collection=new_collection,
                    type=trans_data.get('type') or trans_data.get('transportation_type') or 'other',
                    name=trans_data.get('name') or 'Untitled Transportation',
                    description=trans_data.get('description') or trans_data.get('notes'),
                    rating=trans_data.get('rating'),
                    price=transport_price,
                    price_currency=transport_currency,
                    link=trans_data.get('link'),
                    date=_parse_datetime(trans_data.get('date')),
                    end_date=_parse_datetime(trans_data.get('end_date')),
                    start_timezone=trans_data.get('start_timezone'),
                    end_timezone=trans_data.get('end_timezone'),
                    flight_number=trans_data.get('flight_number'),
                    from_location=trans_data.get('from_location'),
                    to_location=trans_data.get('to_location'),
                    origin=origin,
                    destination=destination,
                    start_code=trans_data.get('start_code'),
                    end_code=trans_data.get('end_code'),
                    is_public=bool(trans_data.get('is_public', False)),
                )

            for note_data in metadata.get('notes', []):
                Note.objects.create(
                    user=request.user,
                    collection=new_collection,
                    name=note_data.get('name') or note_data.get('title') or 'Untitled Note',
                    content=note_data.get('content') or '',
                    links=note_data.get('links') or [],
                    date=_parse_date(note_data.get('date')),
                    is_public=bool(note_data.get('is_public', False)),
                )

            for check_data in metadata.get('checklists', []):
                checklist = Checklist.objects.create(
                    user=request.user,
                    collection=new_collection,
                    name=check_data.get('name') or 'Untitled Checklist',
                    date=_parse_date(check_data.get('date')),
                    is_public=bool(check_data.get('is_public', False)),
                )
                for item_data in check_data.get('items', []):
                    ChecklistItem.objects.create(
                        user=request.user,
                        checklist=checklist,
                        name=item_data.get('name') or 'Untitled Item',
                        is_checked=item_data.get('is_checked', item_data.get('completed', False)),
                    )

            for lodg_data in metadata.get('lodging', []):
                lodging_price, lodging_currency = _parse_money(
                    lodg_data.get('price'),
                    lodg_data.get('price_currency'),
                )
                Lodging.objects.create(
                    user=request.user,
                    collection=new_collection,
                    name=lodg_data.get('name') or 'Untitled Lodging',
                    type=lodg_data.get('type') or lodg_data.get('lodging_type') or 'other',
                    description=lodg_data.get('description') or lodg_data.get('notes'),
                    rating=lodg_data.get('rating'),
                    link=lodg_data.get('link'),
                    check_in=_parse_datetime(lodg_data.get('check_in')),
                    check_out=_parse_datetime(lodg_data.get('check_out')),
                    timezone=lodg_data.get('timezone'),
                    reservation_number=lodg_data.get('reservation_number'),
                    price=lodging_price,
                    price_currency=lodging_currency,
                    coordinates=make_point(lodg_data.get('longitude'), lodg_data.get('latitude')),
                    location=lodg_data.get('location'),
                    is_public=bool(lodg_data.get('is_public', False)),
                )

            # This export carries no itinerary rows; rebuild the day plan from the records' dates.
            if new_collection.type == 'trip':
                imported_day_count = collection_meta.get('day_count')
                if isinstance(imported_day_count, int) and imported_day_count >= 1:
                    day_plan.build_days(new_collection, imported_day_count)
                else:
                    day_plan.convert_collection(new_collection)

            serializer = self.get_serializer(new_collection)
            return Response(serializer.data, status=status.HTTP_201_CREATED)


    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Create a duplicate of an existing collection.

        Copies collection metadata and linked content:
        - locations (linked, not cloned)
        - transportation, notes, checklists (with items), lodging
        - itinerary days and itinerary items
        Shared users are not copied and the new collection is private.
        """
        original = self.get_object()

        # Only the owner can duplicate
        if original.user != request.user:
            return Response(
                {"error": "You do not have permission to duplicate this collection."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            with transaction.atomic():
                new_collection = Collection.objects.create(
                    user=request.user,
                    name=f"Copy of {original.name}",
                    description=original.description,
                    link=original.link,
                    is_public=False,
                    is_archived=False,
                    start_date=original.start_date,
                    end_date=original.end_date,
                    type=original.type,
                )

                # Link existing locations to the new collection
                linked_locations = list(original.locations.all())
                if linked_locations:
                    new_collection.locations.set(linked_locations)

                # Duplicate primary image if it exists so permissions align with the new collection
                if original.primary_image:
                    original_primary = original.primary_image
                    if original_primary.image:
                        try:
                            original_primary.image.open('rb')
                            image_bytes = original_primary.image.read()
                        finally:
                            try:
                                original_primary.image.close()
                            except Exception:
                                pass

                        file_name = (original_primary.image.name or '').split('/')[-1] or 'image.webp'
                        new_primary = ContentImage(
                            user=request.user,
                            image=ContentFile(image_bytes, name=file_name),
                            immich_id=None,
                            is_primary=original_primary.is_primary,
                        )
                    else:
                        new_primary = ContentImage(
                            user=request.user,
                            immich_id=original_primary.immich_id,
                            is_primary=original_primary.is_primary,
                        )

                    new_primary.content_object = new_collection
                    new_primary.save()
                    new_collection.primary_image = new_primary
                    new_collection.save(update_fields=['primary_image'])

                def _copy_generic_media(source_obj, target_obj):
                    # Images
                    for img in source_obj.images.all():
                        if img.image:
                            try:
                                img.image.open('rb')
                                image_bytes = img.image.read()
                            finally:
                                try:
                                    img.image.close()
                                except Exception:
                                    pass

                            file_name = (img.image.name or '').split('/')[-1] or 'image.webp'
                            media = ContentImage(
                                user=request.user,
                                image=ContentFile(image_bytes, name=file_name),
                                immich_id=None,
                                is_primary=img.is_primary,
                            )
                        else:
                            media = ContentImage(
                                user=request.user,
                                immich_id=img.immich_id,
                                is_primary=img.is_primary,
                            )

                        media.content_object = target_obj
                        media.save()

                    # Attachments
                    for attachment in source_obj.attachments.all():
                        try:
                            attachment.file.open('rb')
                            file_bytes = attachment.file.read()
                        finally:
                            try:
                                attachment.file.close()
                            except Exception:
                                pass

                        file_name = (attachment.file.name or '').split('/')[-1] or 'attachment'
                        new_attachment = ContentAttachment(
                            user=request.user,
                            file=ContentFile(file_bytes, name=file_name),
                            name=attachment.name,
                        )
                        new_attachment.content_object = target_obj
                        new_attachment.save()

                # Copy FK-based related content and track ID mapping for itinerary relinks
                object_id_map = {}

                for item in Transportation.objects.filter(collection=original):
                    new_item = Transportation.objects.create(
                        user=request.user,
                        collection=new_collection,
                        type=item.type,
                        name=item.name,
                        description=item.description,
                        rating=item.rating,
                        price=item.price,
                        link=item.link,
                        date=item.date,
                        end_date=item.end_date,
                        start_timezone=item.start_timezone,
                        end_timezone=item.end_timezone,
                        flight_number=item.flight_number,
                        from_location=item.from_location,
                        origin=item.origin,
                        destination=item.destination,
                        start_code=item.start_code,
                        end_code=item.end_code,
                        to_location=item.to_location,
                        is_public=item.is_public,
                    )
                    object_id_map[item.id] = new_item.id
                    _copy_generic_media(item, new_item)

                for item in Note.objects.filter(collection=original):
                    new_item = Note.objects.create(
                        user=request.user,
                        collection=new_collection,
                        name=item.name,
                        content=item.content,
                        links=item.links,
                        date=item.date,
                        is_public=item.is_public,
                    )
                    object_id_map[item.id] = new_item.id
                    _copy_generic_media(item, new_item)

                for item in Lodging.objects.filter(collection=original):
                    new_item = Lodging.objects.create(
                        user=request.user,
                        collection=new_collection,
                        name=item.name,
                        type=item.type,
                        description=item.description,
                        rating=item.rating,
                        link=item.link,
                        check_in=item.check_in,
                        check_out=item.check_out,
                        timezone=item.timezone,
                        reservation_number=item.reservation_number,
                        price=item.price,
                        coordinates=item.coordinates,
                        location=item.location,
                        is_public=item.is_public,
                    )
                    object_id_map[item.id] = new_item.id
                    _copy_generic_media(item, new_item)

                for checklist in Checklist.objects.filter(collection=original):
                    new_checklist = Checklist.objects.create(
                        user=request.user,
                        collection=new_collection,
                        name=checklist.name,
                        date=checklist.date,
                        is_public=checklist.is_public,
                    )
                    object_id_map[checklist.id] = new_checklist.id

                    for checklist_item in checklist.checklistitem_set.all():
                        ChecklistItem.objects.create(
                            user=request.user,
                            checklist=new_checklist,
                            name=checklist_item.name,
                            is_checked=checklist_item.is_checked,
                        )

                # Copy itinerary days and placements; logged visits stay with the original.
                day_map = {}
                for day in CollectionItineraryDay.objects.filter(collection=original):
                    day_map[day.id] = CollectionItineraryDay.objects.create(
                        collection=new_collection,
                        index=day.index,
                        date=day.date,
                        name=day.name,
                        description=day.description,
                    )

                # Copy itinerary items and relink to duplicated FK-based content where applicable
                for item in CollectionItineraryItem.objects.filter(collection=original):
                    CollectionItineraryItem.objects.create(
                        collection=new_collection,
                        content_type=item.content_type,
                        object_id=object_id_map.get(item.object_id, item.object_id),
                        day=day_map.get(item.day_id),
                        date=item.date,
                        is_global=item.is_global,
                        order=item.order,
                        span_end_index=item.span_end_index,
                        is_optional=item.is_optional,
                        start_time=item.start_time,
                        end_time=item.end_time,
                        timezone=item.timezone,
                    )

            serializer = self.get_serializer(new_collection)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to duplicate collection %s", pk)
            return Response(
                {"error": "An error occurred while duplicating the collection."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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
    
    def paginate_and_respond(self, queryset, request):
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)