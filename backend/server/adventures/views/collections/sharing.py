from datetime import timezone as dt_timezone
from django.db import transaction
from django.db.models import Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from django.utils import timezone
from rest_framework import status
from django.conf import settings
from adventures.services import travelers
import logging
from adventures.models import CollectionActivity, CollectionGuestLink, CollectionMember
from adventures.services.activity_log import record_activity
from adventures.models import Collection, CollectionInvite, Location
from adventures.serializers import _build_profile_pic_url
from adventures.views.mixins import preview_response, refuse_anonymous_preview
from adventures.serializers import CollectionInviteSerializer, UltraSlimCollectionSerializer
from adventures.access.audience import can_edit, is_member
from adventures.serializers.sharing import (
    AddTravelersSerializer,
    GuestLinkCreateSerializer,
    InviteCreateSerializer,
    LeaveCollectionSerializer,
    LeavePreviewSerializer,
    MemberRoleSerializer,
    ShareableUserSerializer,
    ShareableUsersQuerySerializer,
    SharingStateSerializer,
)
from core.exceptions import APIError
from core.openapi import ValidationErrorSerializer
from adventures.throttling import SharingPreviewThrottle
from core.parsing import as_uuid
from core.serializers import validated
from django.contrib.auth import get_user_model
from core.visibility import public_access_allowed, shareable_profiles_q

User = get_user_model()
logger = logging.getLogger(__name__)


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
        'allow_public_links': settings.ALLOW_PUBLIC_ACCESS,
        # Admins see how to turn public links on; everyone else is told to ask one.
        'is_admin': bool(getattr(request.user, 'is_staff', False)),
    }


USER_PARAMETER = OpenApiParameter('user_uuid', OpenApiTypes.UUID, OpenApiParameter.PATH, description='The user\'s `uuid`.')
LINK_PARAMETER = OpenApiParameter('link_id', OpenApiTypes.UUID, OpenApiParameter.PATH, description='The guest link id.')
_DELETED = OpenApiResponse(description='Done. No body.')
_ADDED_TRAVELERS = inline_serializer(
    'AddedTravelers',
    {'visits': serializers.IntegerField(), 'locations': serializers.IntegerField()},
)


class SharingActionsMixin:
    """
    Invites, members, guest links, and who a collection is shared with.

    Everything that changes sharing is for the owner only. Others get a 404 for collections
    they cannot see.
    """

    def _owned_collection(self, request, pk):
        if not request.user.is_authenticated:
            raise NotFound('Collection not found.')
        collection = Collection.objects.filter(pk=pk, user=request.user.id).first()
        if collection is None:
            raise NotFound('Collection not found.')
        return collection

    def _sharing_response(self, collection, request, status_code=status.HTTP_200_OK):
        return Response(_sharing_state(collection, request), status=status_code)

    @extend_schema(tags=['Sharing'], responses=SharingStateSerializer)
    @action(detail=True, methods=['get'], url_path='sharing')
    def sharing(self, request, pk=None):
        """
        Get the sharing settings

        Owner only. Members and their roles, invites waiting for an answer, guest links, and
        the public story settings.
        """
        return self._sharing_response(self._owned_collection(request, pk), request)

    @extend_schema(
        tags=['Sharing'],
        request=None,
        responses=inline_serializer(
            'MadeLocationsPrivate',
            {
                'updated': serializers.IntegerField(),
                'location_ids': serializers.ListField(child=serializers.UUIDField()),
            },
        ),
    )
    @action(detail=True, methods=['post'], url_path='make-locations-private')
    def make_locations_private(self, request, pk=None):
        """
        Make the collection's locations private

        Owner only. Turns off `is_public` on every location in the collection that the owner
        owns. Locations that members added stay as they are. Returns how many changed.
        """
        collection = self._owned_collection(request, pk)
        public = Location.objects.filter(collections=collection, user=request.user, is_public=True)
        ids = list(public.values_list('id', flat=True))
        if ids:
            Location.objects.filter(id__in=ids).update(is_public=False, updated_at=timezone.now())
        return Response({'updated': len(ids), 'location_ids': [str(i) for i in ids]})

    # -- Invites -------------------------------------------------------------------------

    @extend_schema(tags=['Sharing'], request=InviteCreateSerializer, responses={201: SharingStateSerializer})
    @action(detail=True, methods=['post'], url_path='invites')
    def create_invite(self, request, pk=None):
        """
        Invite someone

        Owner only. Invites a user whose profile is public or shown to signed-in users, as an
        `editor` or `viewer`. They join when they accept. Returns the updated sharing settings.
        """
        collection = self._owned_collection(request, pk)
        params = validated(InviteCreateSerializer, request.data)
        user = User.objects.filter(shareable_profiles_q(), uuid=params['user']).first()
        if user is None:
            raise NotFound('User not found.')
        if user == request.user:
            raise APIError('You cannot invite yourself.', code='invalid')
        if collection.shared_with.filter(id=user.id).exists():
            raise APIError('This person is already a member.', code='conflict', status=status.HTTP_409_CONFLICT)
        if CollectionInvite.objects.filter(collection=collection, invited_user=user).exists():
            raise APIError('This person has already been invited.', code='conflict', status=status.HTTP_409_CONFLICT)
        CollectionInvite.objects.create(collection=collection, invited_user=user, role=params['role'])
        return self._sharing_response(collection, request, status.HTTP_201_CREATED)

    @extend_schema(tags=['Sharing'], parameters=[USER_PARAMETER], responses={204: _DELETED})
    @action(detail=True, methods=['delete'], url_path=r'invites/(?P<user_uuid>[^/.]+)')
    def revoke_invite(self, request, pk=None, user_uuid=None):
        """Withdraw an invite"""
        collection = self._owned_collection(request, pk)
        invite = CollectionInvite.objects.filter(collection=collection, invited_user__uuid=as_uuid(user_uuid)).first()
        if invite is None:
            raise NotFound('No invite for this person.')
        invite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(tags=['Sharing'], responses=CollectionInviteSerializer(many=True))
    @action(detail=False, methods=['get'], url_path='invitations', pagination_class=None)
    def invitations(self, request):
        """
        List your invitations

        Collections other people invited you to, waiting for you to accept or decline.
        """
        invites = CollectionInvite.objects.filter(invited_user=request.user).select_related('collection__user')
        return Response(CollectionInviteSerializer(invites, many=True).data)

    @extend_schema(tags=['Sharing'], request=None, responses=UltraSlimCollectionSerializer)
    @action(detail=True, methods=['post'], url_path='invitation/accept')
    def accept_invite(self, request, pk=None):
        """
        Accept an invitation

        Joins the collection with the role you were invited with and returns it as a card.
        """
        collection = self.get_object()
        invite = CollectionInvite.objects.filter(collection=collection, invited_user=request.user).first()
        if invite is None:
            raise NotFound('You have no invitation to this collection.')
        collection.shared_with.add(request.user)
        CollectionMember.objects.update_or_create(
            collection=collection, user=request.user, defaults={'role': invite.role}
        )
        record_activity(
            collection, request, CollectionActivity.Verb.MEMBER_ADDED,
            username=request.user.username, role=invite.role,
        )
        invite.delete()
        return Response(UltraSlimCollectionSerializer(collection, context={'request': request}).data)

    @extend_schema(tags=['Sharing'], request=None, responses={204: _DELETED})
    @action(detail=True, methods=['post'], url_path='invitation/decline')
    def decline_invite(self, request, pk=None):
        """Decline an invitation"""
        collection = self.get_object()
        deleted, _ = CollectionInvite.objects.filter(collection=collection, invited_user=request.user).delete()
        if not deleted:
            raise NotFound('You have no invitation to this collection.')
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        tags=['Sharing'], parameters=[ShareableUsersQuerySerializer], responses=ShareableUserSerializer(many=True)
    )
    @action(detail=True, methods=['get'], url_path='shareable-users', pagination_class=None)
    def shareable_users(self, request, pk=None):
        """
        Find people to invite

        Users whose profile is public or shown to signed-in users, who are not the owner, a
        member, or already invited.
        Search with `q`; a `q` of one character returns nothing.
        """
        collection = self.get_object()
        params = validated(ShareableUsersQuerySerializer, request.query_params)
        query = params['q'].strip()
        candidates = (
            User.objects.filter(shareable_profiles_q())
            .exclude(id=collection.user_id)
            .exclude(id__in=collection.shared_with.values('id'))
            .exclude(id__in=CollectionInvite.objects.filter(collection=collection).values('invited_user_id'))
        )
        if query:
            if len(query) < 2:
                return Response([])
            terms = Q()
            for word in query.split()[:3]:
                terms &= Q(username__icontains=word) | Q(first_name__icontains=word) | Q(last_name__icontains=word)
            candidates = candidates.filter(terms)

        users = candidates.order_by('username').only('uuid', 'username', 'first_name', 'last_name', 'profile_pic')
        return Response([
            {
                'uuid': str(user.uuid),
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'profile_pic': _build_profile_pic_url(user),
                'status': 'available',
            }
            for user in users[:params['limit']]
        ])

    # -- Members -------------------------------------------------------------------------

    @extend_schema(
        methods=['PATCH'], tags=['Sharing'], parameters=[USER_PARAMETER], request=MemberRoleSerializer,
        responses=SharingStateSerializer, summary="Change a member's role",
        description='Owner only. Also changes the role of an invite that has not been answered yet.',
    )
    @extend_schema(
        methods=['DELETE'], tags=['Sharing'], parameters=[USER_PARAMETER], request=None,
        responses={204: _DELETED},
        summary='Remove a member',
        description=(
            'Owner only. Places they created in the collection belong to the owner and stay. They keep '
            'their history: each location in it they travelled to, do not own and reach through no other '
            'collection is copied to their account with their visits, and they are taken off the original '
            'visits. A visit they were the only traveler on is deleted, with what others added to it. '
            '`GET …/members/{user_uuid}/removal-preview/` says what that would be.'
        ),
    )
    @action(detail=True, methods=['patch', 'delete'], url_path=r'members/(?P<user_uuid>[^/.]+)')
    def member(self, request, pk=None, user_uuid=None):
        collection = self._owned_collection(request, pk)
        user_uuid = as_uuid(user_uuid)
        user = collection.shared_with.filter(uuid=user_uuid).first() if user_uuid else None

        if request.method == 'DELETE':
            if user is None:
                raise NotFound('That person is not a member of this collection.')
            with transaction.atomic():
                # They never chose to go, so they always keep copies of where they travelled.
                travelers.release_member(collection, user, keep_copies=True)
                collection.shared_with.remove(user)
                collection.save()
                record_activity(collection, request, CollectionActivity.Verb.MEMBER_REMOVED, username=user.username)
            return Response(status=status.HTTP_204_NO_CONTENT)

        role = validated(MemberRoleSerializer, request.data)['role']
        if user is None:
            invite = CollectionInvite.objects.filter(collection=collection, invited_user__uuid=user_uuid).first() \
                if user_uuid else None
            if invite is None:
                raise NotFound('That person is not a member of this collection.')
            invite.role = role
            invite.save(update_fields=['role', 'updated_at'])
        else:
            CollectionMember.objects.update_or_create(collection=collection, user=user, defaults={'role': role})
        return self._sharing_response(collection, request)

    def _member_leaving(self, request, pk):
        """The collection ``request.user`` is a member (not the owner) of, as leaving needs it."""
        collection = self.get_object()
        if request.user == collection.user:
            raise APIError('The owner cannot leave their own collection.', code='invalid')
        if not collection.shared_with.filter(id=request.user.id).exists():
            raise APIError('You are not a member of this collection.', code='invalid')
        return collection

    @extend_schema(
        tags=['Sharing'],
        request=LeaveCollectionSerializer,
        responses={204: _DELETED},
    )
    @action(detail=True, methods=['post'], url_path='leave')
    def leave(self, request, pk=None):
        """
        Leave a collection

        For members. Places you own that are in it stay yours and stay linked, and so do your visits
        at places you still reach through another collection. You are taken off every visit at the
        other locations in it; with `keep_copies` (the default) each of those you travelled to is
        first copied to your account, under its own name, with your visits.
        A visit you were the only traveler on is deleted, with what others added to it.
        `GET …/leave-preview/` says how many locations and such uploads that is.
        """
        collection = self._member_leaving(request, pk)
        keep_copies = validated(LeaveCollectionSerializer, request.data)['keep_copies']
        with transaction.atomic():
            travelers.release_member(collection, request.user, keep_copies)
            collection.shared_with.remove(request.user)
            collection.save()
            record_activity(
                collection, request, CollectionActivity.Verb.MEMBER_REMOVED, username=request.user.username, left=True
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    # -- Travelers -----------------------------------------------------------------------

    @staticmethod
    def _editable_trip(request, pk):
        """The collection, for its owner and editors. 404 for anyone who is not a member."""
        collection_id = as_uuid(pk)
        collection = Collection.objects.filter(pk=collection_id).first() if collection_id else None
        if collection is None or not request.user.is_authenticated or not is_member(request.user, collection):
            raise NotFound('Collection not found.')
        if not can_edit(request.user, collection):
            raise PermissionDenied('You do not have permission to change this collection.')
        return collection

    @extend_schema(
        tags=['Sharing'],
        request=AddTravelersSerializer,
        responses={
            200: _ADDED_TRAVELERS,
            400: OpenApiResponse(
                response=ValidationErrorSerializer,
                description='`traveler_not_allowed`: someone is not the owner or a member of this collection; '
                'or invalid input (`validation_error`, with `fields`).',
            ),
        },
    )
    @action(detail=True, methods=['post'], url_path='add-travelers')
    def add_travelers(self, request, pk=None):
        """
        Add people to this trip's visits

        Owner and editors. For a trip logged before someone joined. Adds the people to the visits
        the trip logged and, when the trip has both a start and an end date, to visits to its locations that started on
        those days (inclusive). Visits on other days are never touched. Returns how many visits
        gained someone and at what locations. `GET …/add-travelers-preview/` counts them first.
        """
        collection = self._editable_trip(request, pk)
        users = validated(AddTravelersSerializer, request.data)['user_uuids']
        return Response(travelers.add_to_trip(collection, users, actor=request))

    # -- Previews ------------------------------------------------------------------------

    @extend_schema(tags=['Sharing'], responses=LeavePreviewSerializer)
    @action(detail=True, methods=['get'], url_path='leave-preview', throttle_classes=[SharingPreviewThrottle])
    def leave_preview(self, request, pk=None):
        """
        Preview leaving a collection

        What `POST …/leave/` would do, changing nothing: how many locations it takes from you
        (each copied when you keep copies) and how many photos, files and activities other people
        added to visits you are the only traveler on, which go with those visits. Members only.
        """
        refuse_anonymous_preview(request)
        collection = self._member_leaving(request, pk)
        return preview_response(LeavePreviewSerializer(travelers.leave_preview(collection, request.user)).data)

    @extend_schema(tags=['Sharing'], parameters=[USER_PARAMETER], responses=LeavePreviewSerializer)
    @action(
        detail=True, methods=['get'], url_path=r'members/(?P<user_uuid>[^/.]+)/removal-preview',
        throttle_classes=[SharingPreviewThrottle],
    )
    def removal_preview(self, request, pk=None, user_uuid=None):
        """
        Preview removing a member

        What `DELETE …/members/{user_uuid}/` would do, changing nothing: the same counts as
        leaving, for them (removal always keeps copies). Owner only.
        """
        refuse_anonymous_preview(request)
        collection = self._owned_collection(request, pk)
        user_uuid = as_uuid(user_uuid)
        user = collection.shared_with.filter(uuid=user_uuid).first() if user_uuid else None
        if user is None:
            raise NotFound('That person is not a member of this collection.')
        return preview_response(LeavePreviewSerializer(travelers.leave_preview(collection, user)).data)

    @extend_schema(
        tags=['Sharing'],
        parameters=[AddTravelersSerializer],
        responses={
            200: _ADDED_TRAVELERS,
            400: OpenApiResponse(
                response=ValidationErrorSerializer,
                description='`traveler_not_allowed`: someone is not the owner or a member; or invalid input '
                '(`validation_error`, with `fields`).',
            ),
        },
    )
    @action(
        detail=True, methods=['get'], url_path='add-travelers-preview', throttle_classes=[SharingPreviewThrottle],
    )
    def add_travelers_preview(self, request, pk=None):
        """
        Preview adding people to this trip's visits

        What `POST …/add-travelers/` would do with the same people, changing nothing: how many
        visits would gain someone, at how many locations. Repeat `user_uuids` for each person
        (`?user_uuids=…&user_uuids=…`). Owner and editors.
        """
        refuse_anonymous_preview(request)
        collection = self._editable_trip(request, pk)
        users = validated(AddTravelersSerializer, request.query_params)['user_uuids']
        return preview_response(travelers.add_to_trip_preview(collection, users))

    # -- Guest links ---------------------------------------------------------------------

    @extend_schema(tags=['Sharing'], request=GuestLinkCreateSerializer, responses={201: SharingStateSerializer})
    @action(detail=True, methods=['post'], url_path='guest-links')
    def create_guest_link(self, request, pk=None):
        """
        Create a guest link

        Owner only. Anyone with the link can open the collection without an account, as an
        `editor` or `viewer`, until it expires or is revoked. Returns the updated sharing
        settings with the new link's `token`. Refused while the server has public access off
        (`ALLOW_PUBLIC_ACCESS`).
        """
        collection = self._owned_collection(request, pk)
        if not public_access_allowed():
            raise APIError('Guest links are turned off on this server.', code='invalid')
        params = validated(GuestLinkCreateSerializer, request.data)
        expires_at = params.get('expires_at')
        if expires_at is not None:
            if timezone.is_naive(expires_at):
                expires_at = timezone.make_aware(expires_at, dt_timezone.utc)
            if expires_at <= timezone.now():
                raise APIError('The expiry must be in the future.', code='invalid')
        CollectionGuestLink.objects.create(
            collection=collection, role=params['role'], label=params['label'], expires_at=expires_at,
        )
        return self._sharing_response(collection, request, status.HTTP_201_CREATED)

    @extend_schema(tags=['Sharing'], parameters=[LINK_PARAMETER], responses={204: _DELETED})
    @action(detail=True, methods=['delete'], url_path=r'guest-links/(?P<link_id>[^/.]+)')
    def revoke_guest_link(self, request, pk=None, link_id=None):
        """
        Revoke a guest link

        Owner only. The link stops working at once and stays listed as revoked.
        """
        collection = self._owned_collection(request, pk)
        link = CollectionGuestLink.objects.filter(collection=collection, pk=as_uuid(link_id)).first() \
            if as_uuid(link_id) else None
        if link is None:
            raise NotFound('Guest link not found.')
        if link.revoked_at is None:
            link.revoked_at = timezone.now()
            link.save(update_fields=['revoked_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

