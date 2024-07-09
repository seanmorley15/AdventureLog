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