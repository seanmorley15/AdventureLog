from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the object.
        return obj.user_id == request.user


class IsPublicReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow read-only access to public objects,
    and write access to the owner of the object.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed if the object is public
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or obj.user_id == request.user

        # Write permissions are only allowed to the owner of the object
        return obj.user_id == request.user
    
class CollectionShared(permissions.BasePermission):
    """
    Custom permission to only allow read-only access to public objects,
    and write access to the owner of the object.
    """

    def has_object_permission(self, request, view, obj):

        # Read permissions are allowed if the object is shared with the user
        if obj.shared_with and obj.shared_with.filter(id=request.user.id).exists():
            return True
        
        # Write permissions are allowed if the object is shared with the user
        if request.method not in permissions.SAFE_METHODS and obj.shared_with.filter(id=request.user.id).exists():
            return True

        # Read permissions are allowed if the object is public
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or obj.user_id == request.user

        # Write permissions are only allowed to the owner of the object
        return obj.user_id == request.user

class IsOwnerOrSharedWithFullAccess(permissions.BasePermission):
    """
    Custom permission to allow:
    - Full access for shared users
    - Full access for owners
    - Read-only access for others on safe methods
    """

    def has_object_permission(self, request, view, obj):
        # Check if the object has a collection
        if hasattr(obj, 'collection') and obj.collection:
            # Allow all actions for shared users
            if request.user in obj.collection.shared_with.all():
                return True

        # Always allow GET, HEAD, or OPTIONS requests (safe methods)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Allow all actions for the owner
        return obj.user_id == request.user

class IsPublicOrOwnerOrSharedWithFullAccess(permissions.BasePermission):
    """
    Custom permission to allow:
    - Read-only access for public objects
    - Full access for shared users
    - Full access for owners
    """

    def has_object_permission(self, request, view, obj):
        # Allow read-only access for public objects
        if obj.is_public and request.method in permissions.SAFE_METHODS:
            return True

        # Check if the object has a collection
        if hasattr(obj, 'collection') and obj.collection:
            # Allow all actions for shared users
            if request.user in obj.collection.shared_with.all():
                return True

        # Allow all actions for the owner
        return obj.user_id == request.user