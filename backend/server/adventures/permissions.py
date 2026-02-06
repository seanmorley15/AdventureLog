from rest_framework import permissions
from django.conf import settings

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
    Permission class for collection sharing functionality.
    
    This permission handles access control for collections and objects that are shared
    through collections. It supports:
    
    - Collection invite acceptance/declining for users with pending invites
    - Full access for collection owners and shared users
    - Read-only access for public objects (anonymous and authenticated users)
    - Write access for owners and users shared via collections
    
    Access Rules:
    - Anonymous users: read-only access to public objects
    - Invited users: can accept/decline invites for collections they're invited to
    - Collection owners: full access to their collections and related objects
    - Shared users: full access to collections they're shared with and related objects
    - Public access: read-only for objects marked as public
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            # Anonymous: only read public
            return request.method in permissions.SAFE_METHODS and getattr(obj, 'is_public', False)

        # Special case for accept_invite and decline_invite actions
        # Allow access if user has a pending invite for this collection
        if hasattr(view, 'action') and view.action in ['accept_invite', 'decline_invite']:
            if hasattr(obj, 'invites'):
                if obj.invites.filter(invited_user=user).exists():
                    return True

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
            return getattr(obj, 'is_public', False) or getattr(obj, 'user', None) == user

        # Write permission only if owner or shared user via collections
        if getattr(obj, 'user', None) == user:
            return True

        if hasattr(obj, 'collections'):
            if obj.collections.filter(shared_with=user).exists():
                return True

        # Default deny
        return False


class IsOwnerOrSharedWithFullAccess(permissions.BasePermission):
    """
    Permission class that provides access control based on ownership and sharing.
    
    Access Rules:
    - Object owners have full access (read/write)
    - Users shared via collections have full access (read/write)
    - Collection owners have full access to objects in their collections
    - Users with direct sharing have full access
    - Anonymous users get read-only access to public objects
    - Authenticated users get read-only access to public objects
    
    Supports multiple sharing patterns:
    - obj.collections (many-to-many collections)
    - obj.collection (single collection foreign key)
    - obj.shared_with (direct sharing many-to-many)
    - obj.is_public (public access flag)
    """
    
    def has_object_permission(self, request, view, obj):
        """
        Check if the user has permission to access the object.
        
        Args:
            request: The HTTP request
            view: The view being accessed
            obj: The object being accessed
            
        Returns:
            bool: True if access is granted, False otherwise
        """
        user = request.user
        is_safe_method = request.method in permissions.SAFE_METHODS

        # If the object has a location field, get that location and continue checking with that object, basically from the location's perspective. I am very proud of this line of code and that's why I am writing this comment.

        if type(obj).__name__ == 'Trail':
            obj = obj.location

        if type(obj).__name__ == 'Activity':
            # If the object is an Activity, get its location
            if hasattr(obj, 'visit') and hasattr(obj.visit, 'location'):
                obj = obj.visit.location

        
        if type(obj).__name__ == 'Visit':
            # If the object is a Visit, get its location
            if hasattr(obj, 'location'):
                obj = obj.location

        if type(obj).__name__ == 'CollectionItineraryItem':
            if hasattr(obj, 'object_id') and hasattr(obj, 'content_type'):
                content_object = obj.content_type.get_object_for_this_type(id=obj.object_id)
                obj = content_object

        # Anonymous users only get read access to public objects
        if not user or not user.is_authenticated:
            return is_safe_method and getattr(obj, 'is_public', False)

        # Collaborative mode: authenticated users can edit public content
        if getattr(settings, 'COLLABORATIVE_MODE', False) and getattr(obj, 'is_public', False):
            return True

        # Owner always has full access
        if self._is_owner(obj, user):
            return True
        
        # Check collection-based access (both ownership and sharing)
        if self._has_collection_access(obj, user):
            return True
        
        # Check direct sharing
        if self._has_direct_sharing_access(obj, user):
            return True
        
        # For safe methods, check if object is public
        if is_safe_method and getattr(obj, 'is_public', False):
            return True
        
        return False
    
    def _is_owner(self, obj, user):
        """
        Check if the user is the owner of the object.
        
        Args:
            obj: The object to check
            user: The user to check ownership for
            
        Returns:
            bool: True if user owns the object
        """
        return hasattr(obj, 'user') and obj.user == user
    
    def _has_collection_access(self, obj, user):
        """
        Check if user has access via collections (either as owner or shared user).
        
        Handles both many-to-many collections and single collection foreign keys.
        
        Args:
            obj: The object to check
            user: The user to check access for
            
        Returns:
            bool: True if user has collection-based access
        """
        # Check many-to-many collections (obj.collections)
        if hasattr(obj, 'collections'):
            collections = obj.collections.all()
            if collections.exists():
                # User is shared with any collection containing this object
                if collections.filter(shared_with=user).exists():
                    return True
                # User owns any collection containing this object
                if collections.filter(user=user).exists():
                    return True
        
        # Check single collection foreign key (obj.collection)
        if hasattr(obj, 'collection') and obj.collection:
            collection = obj.collection
            # User is shared with the collection
            if hasattr(collection, 'shared_with') and collection.shared_with.filter(id=user.id).exists():
                return True
            # User owns the collection
            if hasattr(collection, 'user') and collection.user == user:
                return True
        
        return False
    
    def _has_direct_sharing_access(self, obj, user):
        """
        Check if user has direct sharing access to the object.
        
        Args:
            obj: The object to check
            user: The user to check access for
            
        Returns:
            bool: True if user has direct sharing access
        """
        return (hasattr(obj, 'shared_with') and 
                obj.shared_with.filter(id=user.id).exists())
    
    def has_permission(self, request, view):
        """
        Check if the user has permission to access the view.
        
        This is called before has_object_permission and provides a way to
        deny access at the view level (e.g., for unauthenticated users).
        
        Args:
            request: The HTTP request
            view: The view being accessed
            
        Returns:
            bool: True if access is granted at the view level
        """
        # Allow authenticated users and anonymous users for safe methods
        # Individual object permissions are handled in has_object_permission
        return (request.user and request.user.is_authenticated) or \
               request.method in permissions.SAFE_METHODS
    

class ContentImagePermission(IsOwnerOrSharedWithFullAccess):
    """
    Specialized permission for ContentImage objects that checks permissions
    on the related content object.

    In collaborative mode, users can only delete their own images.
    """

    def has_object_permission(self, request, view, obj):
        """
        For ContentImage objects, check permissions on the related content object.
        For DELETE operations in collaborative mode, only allow image owner to delete.
        """
        if not request.user or not request.user.is_authenticated:
            return False

        # Get the related content object
        content_object = obj.content_object
        if not content_object:
            return False

        # Check if this is a delete operation (DELETE method or image_delete action which uses POST)
        is_delete_operation = (
            request.method == 'DELETE' or
            (hasattr(view, 'action') and view.action == 'image_delete')
        )

        # In collaborative mode, only allow deleting your own uploads
        # Even location owners cannot delete files uploaded by others
        if is_delete_operation and getattr(settings, 'COLLABORATIVE_MODE', False):
            # Only the uploader can delete their own files
            if obj.user == request.user:
                return True
            # Otherwise, deny deletion
            return False

        # Use the parent permission class to check access to the content object
        return super().has_object_permission(request, view, content_object)