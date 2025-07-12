from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from django.core.files.base import ContentFile
from django.contrib.contenttypes.models import ContentType
from adventures.models import Location, Transportation, Note, Lodging, Visit, ContentImage
from adventures.serializers import ContentImageSerializer
from integrations.models import ImmichIntegration
import uuid
import requests

class ContentImageViewSet(viewsets.ModelViewSet):
    serializer_class = ContentImageSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def image_delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def toggle_primary(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        
        instance = self.get_object()
        content_object = instance.content_object
        
        # Check ownership based on content type
        if hasattr(content_object, 'user') and content_object.user != request.user:
            return Response({"error": "User does not own this content"}, status=status.HTTP_403_FORBIDDEN)
        
        # Check if the image is already the primary image
        if instance.is_primary:
            return Response({"error": "Image is already the primary image"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Set other images of the same content object to not primary
        ContentImage.objects.filter(
            content_type=instance.content_type,
            object_id=instance.object_id,
            is_primary=True
        ).update(is_primary=False)

        # Set the new image to primary
        instance.is_primary = True
        instance.save()
        return Response({"success": "Image set as primary image"})

    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Get content type and object ID from request
        content_type_name = request.data.get('content_type')
        object_id = request.data.get('object_id')
        
        if not content_type_name or not object_id:
            return Response({
                "error": "content_type and object_id are required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
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
        
        # Get the content type and object
        try:
            content_type = ContentType.objects.get_for_model(content_type_map[content_type_name])
            content_object = content_type_map[content_type_name].objects.get(id=object_id)
        except (ValueError, content_type_map[content_type_name].DoesNotExist):
            return Response({
                "error": f"{content_type_name} not found"
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check permissions based on content type
        if hasattr(content_object, 'user'):
            if content_object.user != request.user:
                # For Location, check if user has shared access
                if content_type_name == 'location':
                    if content_object.collections.exists():
                        user_has_access = False
                        for collection in content_object.collections.all():
                            if collection.shared_with.filter(id=request.user.id).exists() or collection.user == request.user:
                                user_has_access = True
                                break
                        
                        if not user_has_access:
                            return Response({
                                "error": "User does not have permission to access this content"
                            }, status=status.HTTP_403_FORBIDDEN)
                    else:
                        return Response({
                            "error": "User does not own this content"
                        }, status=status.HTTP_403_FORBIDDEN)
                else:
                    return Response({
                        "error": "User does not own this content"
                    }, status=status.HTTP_403_FORBIDDEN)
        
        # Handle Immich ID for shared users by downloading the image
        if (hasattr(content_object, 'user') and 
            request.user != content_object.user and 
            'immich_id' in request.data and 
            request.data.get('immich_id')):
            
            immich_id = request.data.get('immich_id')
            
            # Get the shared user's Immich integration
            try:
                user_integration = ImmichIntegration.objects.get(user=request.user)
            except ImmichIntegration.DoesNotExist:
                return Response({
                    "error": "No Immich integration found for your account. Please set up Immich integration first.",
                    "code": "immich_integration_not_found"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Download the image from the shared user's Immich server
            try:
                immich_response = requests.get(
                    f'{user_integration.server_url}/assets/{immich_id}/thumbnail?size=preview',
                    headers={'x-api-key': user_integration.api_key},
                    timeout=10
                )
                immich_response.raise_for_status()
                
                # Create a temporary file with the downloaded content
                content_type_header = immich_response.headers.get('Content-Type', 'image/jpeg')
                if not content_type_header.startswith('image/'):
                    return Response({
                        "error": "Invalid content type returned from Immich server.",
                        "code": "invalid_content_type"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Determine file extension from content type
                ext_map = {
                    'image/jpeg': '.jpg',
                    'image/png': '.png',
                    'image/webp': '.webp',
                    'image/gif': '.gif'
                }
                file_ext = ext_map.get(content_type_header, '.jpg')
                filename = f"immich_{immich_id}{file_ext}"
                
                # Create a Django ContentFile from the downloaded image
                image_file = ContentFile(immich_response.content, name=filename)
                
                # Modify request data to use the downloaded image instead of immich_id
                request_data = request.data.copy()
                request_data.pop('immich_id', None)  # Remove immich_id
                request_data['image'] = image_file  # Add the image file
                request_data['content_type'] = content_type.id
                request_data['object_id'] = object_id
                
                # Create the serializer with the modified data
                serializer = self.get_serializer(data=request_data)
                serializer.is_valid(raise_exception=True)
                
                # Save with the downloaded image
                serializer.save(
                    user=content_object.user if hasattr(content_object, 'user') else request.user,
                    image=image_file,
                    content_type=content_type,
                    object_id=object_id
                )
                
                return Response(serializer.data, status=status.HTTP_201_CREATED)
                
            except requests.exceptions.RequestException:
                return Response({
                    "error": f"Failed to fetch image from Immich server",
                    "code": "immich_fetch_failed"
                }, status=status.HTTP_502_BAD_GATEWAY)
            except Exception:
                return Response({
                    "error": f"Unexpected error processing Immich image",
                    "code": "immich_processing_error"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Add content type and object ID to request data
        request_data = request.data.copy()
        request_data['content_type'] = content_type.id
        request_data['object_id'] = object_id
        
        # Create serializer with modified data
        serializer = self.get_serializer(data=request_data)
        serializer.is_valid(raise_exception=True)
        
        # Save the image
        serializer.save(
            user=content_object.user if hasattr(content_object, 'user') else request.user,
            content_type=content_type,
            object_id=object_id
        )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        
        instance = self.get_object()
        content_object = instance.content_object
        
        # Check ownership
        if hasattr(content_object, 'user') and content_object.user != request.user:
            return Response({"error": "User does not own this content"}, status=status.HTTP_403_FORBIDDEN)
        
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        
        instance = self.get_object()
        content_object = instance.content_object
        
        # Check ownership
        if hasattr(content_object, 'user') and content_object.user != request.user:
            return Response({"error": "User does not own this content"}, status=status.HTTP_403_FORBIDDEN)
        
        return super().destroy(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        
        instance = self.get_object()
        content_object = instance.content_object
        
        # Check ownership
        if hasattr(content_object, 'user') and content_object.user != request.user:
            return Response({"error": "User does not own this content"}, status=status.HTTP_403_FORBIDDEN)
        
        return super().partial_update(request, *args, **kwargs)
    


    def get_queryset(self):
        """Get all images the user has access to"""
        if not self.request.user.is_authenticated:
            return ContentImage.objects.none()
        
        # Get content type for Location to handle shared access
        location_content_type = ContentType.objects.get_for_model(Location)
        
        # Build queryset with proper permissions
        queryset = ContentImage.objects.filter(
            Q(content_object__user=self.request.user) |  # User owns the content
            Q(content_type=location_content_type, content_object__collections__shared_with=self.request.user)  # Shared locations
        ).distinct()
        
        return queryset

    def perform_create(self, serializer):
        # The content_type and object_id are already set in the create method
        # Just ensure the user is set correctly
        pass