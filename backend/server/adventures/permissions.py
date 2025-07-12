from rest_framework import permissions

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
    Allow full access if user is in shared_with of collection(s) or owner,
    read-only if public or shared_with,
    write only if owner or shared_with.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            # Anonymous: only read public
            return request.method in permissions.SAFE_METHODS and obj.is_public

        # Check if user is in shared_with of any collections related to the obj
        # If obj is a Collection itself:
        if hasattr(obj, 'shared_with'):
            if obj.shared_with.filter(id=user.id).exists():
                return True

        # If obj is a Location (has collections M2M)
        if hasattr(obj, 'collections'):
            # Check if user is in shared_with of any related collection
            shared_collections = obj.collections.filter(shared_with=user)
            if shared_collections.exists():
                return True

        # Read permission if public or owner
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or obj.user == user

        # Write permission only if owner or shared user via collections
        if obj.user == user:
            return True

        if hasattr(obj, 'collections'):
            if obj.collections.filter(shared_with=user).exists():
                return True

        # Default deny
        return False


class IsOwnerOrSharedWithFullAccess(permissions.BasePermission):
    """
    Full access for owners and users shared via collections,
    read-only for others if public.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return request.method in permissions.SAFE_METHODS and obj.is_public

        # If safe method (read), allow if:
        if request.method in permissions.SAFE_METHODS:
            if obj.is_public:
                return True
            if obj.user == user:
                return True
            # If user in shared_with of any collection related to obj
            if hasattr(obj, 'collections') and obj.collections.filter(shared_with=user).exists():
                return True
            # **FIX: Check if user OWNS any collection that contains this object**
            if hasattr(obj, 'collections') and obj.collections.filter(user=user).exists():
                return True
            if hasattr(obj, 'collection') and obj.collection and obj.collection.shared_with.filter(id=user.id).exists():
                return True
            if hasattr(obj, 'collection') and obj.collection and obj.collection.user == user:
                return True
            if hasattr(obj, 'shared_with') and obj.shared_with.filter(id=user.id).exists():
                return True
            return False

        # For write methods, allow if owner or shared user
        if obj.user == user:
            return True
        if hasattr(obj, 'collections') and obj.collections.filter(shared_with=user).exists():
            return True
        # **FIX: Allow write access if user owns any collection containing this object**
        if hasattr(obj, 'collections') and obj.collections.filter(user=user).exists():
            return True
        if hasattr(obj, 'collection') and obj.collection and obj.collection.shared_with.filter(id=user.id).exists():
            return True
        if hasattr(obj, 'collection') and obj.collection and obj.collection.user == user:
            return True
        if hasattr(obj, 'shared_with') and obj.shared_with.filter(id=user.id).exists():
            return True

        return False