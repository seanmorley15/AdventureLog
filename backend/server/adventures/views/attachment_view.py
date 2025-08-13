from rest_framework import viewsets, status
from django.db.models import Q
from rest_framework.response import Response
from django.contrib.contenttypes.models import ContentType
from adventures.models import Location, Transportation, Note, Lodging, Visit, ContentAttachment
from adventures.serializers import AttachmentSerializer
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from adventures.permissions import ContentImagePermission


class AttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = AttachmentSerializer
    permission_classes = [ContentImagePermission]

    def get_queryset(self):
        """Get all images the user has access to"""
        if not self.request.user.is_authenticated:
            return ContentAttachment.objects.none()
        
        # Import here to avoid circular imports
        from adventures.models import Location, Transportation, Note, Lodging, Visit
        
        # Build a single query with all conditions
        return ContentAttachment.objects.filter(
            # User owns the image directly (if user field exists on ContentImage)
            Q(user=self.request.user) |
            
            # Or user has access to the content object
            (
                # Locations owned by user
                Q(content_type=ContentType.objects.get_for_model(Location)) &
                Q(object_id__in=Location.objects.filter(user=self.request.user).values_list('id', flat=True))
            ) |
            (
                # Shared locations
                Q(content_type=ContentType.objects.get_for_model(Location)) &
                Q(object_id__in=Location.objects.filter(collections__shared_with=self.request.user).values_list('id', flat=True))
            ) |
            (
                # Collections owned by user containing locations
                Q(content_type=ContentType.objects.get_for_model(Location)) &
                Q(object_id__in=Location.objects.filter(collections__user=self.request.user).values_list('id', flat=True))
            ) |
            (
                # Transportation owned by user
                Q(content_type=ContentType.objects.get_for_model(Transportation)) &
                Q(object_id__in=Transportation.objects.filter(user=self.request.user).values_list('id', flat=True))
            ) |
            (
                # Notes owned by user
                Q(content_type=ContentType.objects.get_for_model(Note)) &
                Q(object_id__in=Note.objects.filter(user=self.request.user).values_list('id', flat=True))
            ) |
            (
                # Lodging owned by user
                Q(content_type=ContentType.objects.get_for_model(Lodging)) &
                Q(object_id__in=Lodging.objects.filter(user=self.request.user).values_list('id', flat=True))
            ) |
            (
                # Notes shared with user
                Q(content_type=ContentType.objects.get_for_model(Note)) &
                Q(object_id__in=Note.objects.filter(collection__shared_with=self.request.user).values_list('id', flat=True))
            ) |
            (
                # Lodging shared with user
                Q(content_type=ContentType.objects.get_for_model(Lodging)) &
                Q(object_id__in=Lodging.objects.filter(collection__shared_with=self.request.user).values_list('id', flat=True))
            ) |
            (
                # Transportation shared with user
                Q(content_type=ContentType.objects.get_for_model(Transportation)) &
                Q(object_id__in=Transportation.objects.filter(collection__shared_with=self.request.user).values_list('id', flat=True))
            ) |
            (
                # Visits - access through location's user
                Q(content_type=ContentType.objects.get_for_model(Visit)) &
                Q(object_id__in=Visit.objects.filter(location__user=self.request.user).values_list('id', flat=True))
            ) |
            (
                # Visits - access through shared locations
                Q(content_type=ContentType.objects.get_for_model(Visit)) &
                Q(object_id__in=Visit.objects.filter(location__collections__shared_with=self.request.user).values_list('id', flat=True))
            ) |
            (
                # Visits - access through collections owned by user
                Q(content_type=ContentType.objects.get_for_model(Visit)) &
                Q(object_id__in=Visit.objects.filter(location__collections__user=self.request.user).values_list('id', flat=True))
            )
        ).distinct()

    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Get content type and object ID from request
        content_type_name = request.data.get('content_type')
        object_id = request.data.get('object_id')
        
        # For backward compatibility, also check for 'location' parameter
        location_id = request.data.get('location')
        
        if location_id and not (content_type_name and object_id):
            # Handle legacy location-specific requests
            content_type_name = 'location'
            object_id = location_id
        
        if not content_type_name or not object_id:
            return Response({"error": "content_type and object_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Get and validate the content object
        content_object = self._get_and_validate_content_object(content_type_name, object_id)
        if isinstance(content_object, Response):  # Error response
            return content_object

        return super().create(request, *args, **kwargs)

    def _get_and_validate_content_object(self, content_type_name, object_id):
        """Get and validate the content object exists and user has access"""
        # Map content type names to model classes
        content_type_map = {
            'location': Location,
            'transportation': Transportation,
            'note': Note,
            'lodging': Lodging,
            'visit': Visit,
        }
        
        if content_type_name not in content_type_map:
            return Response({
                "error": f"Invalid content_type. Must be one of: {', '.join(content_type_map.keys())}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the content object
        try:
            content_object = content_type_map[content_type_name].objects.get(id=object_id)
        except (ValueError, content_type_map[content_type_name].DoesNotExist):
            return Response({
                "error": f"{content_type_name} not found"
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check permissions using the permission class
        permission_checker = IsOwnerOrSharedWithFullAccess()
        if not permission_checker.has_object_permission(self.request, self, content_object):
            return Response({
                "error": "User does not have permission to access this content"
            }, status=status.HTTP_403_FORBIDDEN)
        
        return content_object

    def perform_create(self, serializer):
        content_type_name = self.request.data.get('content_type')
        object_id = self.request.data.get('object_id')
        
        # Handle legacy location parameter
        location_id = self.request.data.get('location')
        if location_id and not (content_type_name and object_id):
            content_type_name = 'location'
            object_id = location_id

        # Get the content object (we know it exists from create validation)
        content_type_map = {
            'location': Location,
            'transportation': Transportation,
            'note': Note,
            'lodging': Lodging,
            'visit': Visit,
        }
        
        model_class = content_type_map[content_type_name]
        content_object = model_class.objects.get(id=object_id)
        content_type = ContentType.objects.get_for_model(model_class)

        # Determine the appropriate user to assign
        attachment_user = self._get_attachment_user(content_object)
        
        serializer.save(
            user=attachment_user,
            content_type=content_type,
            object_id=object_id
        )

    def _get_attachment_user(self, content_object):
        """
        Determine which user should own the attachment based on the content object.
        This preserves the original logic for shared collections.
        """
        # Handle Location objects
        if isinstance(content_object, Location):
            if content_object.collections.exists():
                # Get the first collection's owner (assuming all collections have the same owner)
                collection = content_object.collections.first()
                return collection.user
            else:
                return self.request.user
        
        # Handle other content types with collections
        elif hasattr(content_object, 'collection') and content_object.collection:
            return content_object.collection.user
        
        # Handle content objects with a user field
        elif hasattr(content_object, 'user'):
            return content_object.user
        
        # Default to request user
        return self.request.user