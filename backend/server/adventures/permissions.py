from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

from adventures.access.audience import audience_for_request, can_edit, has_guest_token, is_member

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Owners can edit, others have read-only access.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        # obj.user is FK to User, compare with request.user
        return obj.user == request.user


class IsPublicReadOnly(permissions.BasePermission):
    """
    Read-only if public or owner, write only for owner.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or obj.user == request.user
        return obj.user == request.user


class CollectionShared(permissions.BasePermission):
    """
    Access to a collection itself.

    Reads follow the audience: members and guest links see the plan, and a
    public reader sees the story. Changing the collection record (visibility,
    members, delete) is owner-only. Members may leave, and invited users may
    accept or decline.
    """
    def has_permission(self, request, view):
        return (request.user and request.user.is_authenticated) or \
               request.method in permissions.SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        user = request.user
        if obj.__class__.__name__ != 'Collection':
            return False

        if request.method in permissions.SAFE_METHODS:
            return audience_for_request(request, obj) is not None

        if not user or not user.is_authenticated:
            return False

        action = getattr(view, 'action', None)
        if action in ('accept_invite', 'decline_invite'):
            return obj.invites.filter(invited_user=user).exists()
        if action == 'leave':
            return is_member(request, obj)
        return obj.user_id == user.id


class IsOwnerOrSharedWithFullAccess(permissions.BasePermission):
    """
    Records reached through a collection follow that collection's audience.

    - Owners of the record have full access.
    - Collection owners, editors, and guest editors can change records in it.
    - Viewers and guest viewers can read them and change nothing.
    - ``is_public`` still opens a location (its own page) and records that are
      not in a collection. It does not open lodging, transport, notes, or
      checklists that belong to a collection, and it never grants a write.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        is_safe_method = request.method in permissions.SAFE_METHODS

        def collection_allows(collection):
            if collection is None:
                return False
            return is_member(request, collection) if is_safe_method else can_edit(request, collection)

        # Day-owned activities and trails belong to the collection's members.
        # Do not follow visit.location or trail.location when that parent is null,
        # and do not treat a public collection as permission to read the file.
        if type(obj).__name__ == 'Trail' and obj.location_id is None:
            return collection_allows(obj.day.collection if obj.day_id else obj.collection)

        if type(obj).__name__ == 'Activity' and obj.visit_id is None:
            return collection_allows(obj.day.collection if obj.day_id else obj.collection)

        if type(obj).__name__ == 'CollectionItineraryDay':
            return collection_allows(obj.collection)

        if type(obj).__name__ == 'CollectionItineraryItem':
            return collection_allows(obj.collection)

        if type(obj).__name__ == 'Trail':
            obj = obj.location

        if type(obj).__name__ == 'Activity':
            # Place activities are reached through the visit's location.
            if obj.visit_id and getattr(obj.visit, 'location', None) is not None:
                obj = obj.visit.location

        if type(obj).__name__ == 'Visit':
            if hasattr(obj, 'location'):
                obj = obj.location

        authenticated = bool(user and user.is_authenticated)

        # Owner always has full access
        if authenticated and self._is_owner(obj, user):
            return True

        # Collection-based access (owner, members, guest links)
        if self._has_collection_access(request, obj, is_safe_method):
            return True

        # Check direct sharing
        if authenticated and self._has_direct_sharing_access(obj, user):
            return True

        # A record's own public flag opens it for reading, unless a collection owns it.
        if is_safe_method and getattr(obj, 'is_public', False):
            return getattr(obj, 'collection_id', None) is None

        return False

    def _is_owner(self, obj, user):
        return hasattr(obj, 'user') and obj.user == user

    def _has_collection_access(self, request, obj, is_safe_method):
        check = is_member if is_safe_method else can_edit
        if hasattr(obj, 'collections'):
            for collection in obj.collections.all():
                if check(request, collection):
                    return True
        if hasattr(obj, 'collection') and obj.collection:
            if check(request, obj.collection):
                return True
        return False

    def _has_direct_sharing_access(self, obj, user):
        return (obj.__class__.__name__ != 'Collection' and hasattr(obj, 'shared_with') and
                obj.shared_with.filter(id=user.id).exists())

    def has_permission(self, request, view):
        # Authenticated users, anonymous reads, and requests carrying a live guest link.
        # Object permissions decide the rest.
        return (request.user and request.user.is_authenticated) or \
               request.method in permissions.SAFE_METHODS or \
               has_guest_token(request)
    

class ContentImagePermission(IsOwnerOrSharedWithFullAccess):
    """
    Specialized permission for ContentImage objects that checks permissions
    on the related content object.
    """
    
    def has_object_permission(self, request, view, obj):
        """
        For ContentImage objects, check permissions on the related content object.
        """
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Get the related content object
        content_object = obj.content_object
        if not content_object:
            return False
        
        # Use the parent permission class to check access to the content object
        return super().has_object_permission(request, view, content_object)


def ensure_can_change_collection(request, instance, validated_data):
    """
    Guard a change to a record's ``collection`` (lodging, transport, notes, checklists).

    Only the owner of both the record and the collection involved may move a record
    into another collection, and only the owner of the current collection may take it
    out. A request that does not send ``collection`` leaves it alone, so collaborators
    can still edit other fields. Call from ``perform_update`` so PUT and PATCH agree.
    """
    if 'collection' not in validated_data:
        return

    new_collection = validated_data['collection']
    old_collection = instance.collection
    if (new_collection.pk if new_collection else None) == (old_collection.pk if old_collection else None):
        return

    user = request.user
    if new_collection is not None:
        if new_collection.user_id != user.id or instance.user_id != user.id:
            raise PermissionDenied("You do not have permission to use this collection.")
    elif old_collection is not None and old_collection.user_id != user.id:
        raise PermissionDenied("You cannot remove the collection as you are not the owner.")


def ensure_can_add_to_collections(request, collections, noun):
    """Refuse unless the requester can edit every collection a new ``noun`` is being added to."""
    for collection in collections:
        if not can_edit(request, collection):
            raise PermissionDenied(
                f"You don't have permission to add {noun} to collection '{collection.name}'"
            )
