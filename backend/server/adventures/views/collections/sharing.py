from datetime import datetime, timezone as dt_timezone
from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from django.utils import timezone
from rest_framework import status
from django.conf import settings
import logging
from adventures.models import CollectionActivity, CollectionGuestLink, CollectionMember
from adventures.services.activity_log import record_activity
from adventures.models import Collection, CollectionInvite
from adventures.serializers import _build_profile_pic_url
from adventures.serializers import CollectionInviteSerializer
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)



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


class SharingActionsMixin:
    """Invites, members, guest links, and who a collection is shared with."""

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
        CollectionInvite.objects.create(
            collection=collection,
            invited_user=user,
            role=role,
        )
        
        return Response({"success": f"Invite sent to {user.username}"})

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
