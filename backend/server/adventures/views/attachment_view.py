from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.contenttypes.models import ContentType
from adventures.models import Location, ContentAttachment
from adventures.serializers import AttachmentSerializer
from adventures.permissions import IsOwnerOrSharedWithFullAccess


class AttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = AttachmentSerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess]

    def get_queryset(self):
        return ContentAttachment.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Get the content object details
        content_type_id = request.data.get('content_type')
        object_id = request.data.get('object_id')
        
        # For backward compatibility, also check for 'location' parameter
        location_id = request.data.get('location')
        
        if location_id and not (content_type_id and object_id):
            # Handle legacy location-specific requests
            try:
                location = Location.objects.get(id=location_id)
                content_type = ContentType.objects.get_for_model(Location)
                content_type_id = content_type.id
                object_id = location_id
            except Location.DoesNotExist:
                return Response({"error": "Location not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if not (content_type_id and object_id):
            return Response({"error": "content_type and object_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            content_type = ContentType.objects.get(id=content_type_id)
            model_class = content_type.model_class()
            content_object = model_class.objects.get(id=object_id)
        except (ContentType.DoesNotExist, model_class.DoesNotExist):
            return Response({"error": "Content object not found"}, status=status.HTTP_404_NOT_FOUND)

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        content_type_id = self.request.data.get('content_type')
        object_id = self.request.data.get('object_id')
        
        # Handle legacy location parameter
        location_id = self.request.data.get('location')
        if location_id and not (content_type_id and object_id):
            content_type = ContentType.objects.get_for_model(Location)
            content_type_id = content_type.id
            object_id = location_id

        content_type = ContentType.objects.get(id=content_type_id)
        model_class = content_type.model_class()
        content_object = model_class.objects.get(id=object_id)

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