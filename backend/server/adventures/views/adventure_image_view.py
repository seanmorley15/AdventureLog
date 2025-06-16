from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from django.core.files.base import ContentFile
from adventures.models import Adventure, AdventureImage
from adventures.serializers import AdventureImageSerializer
from integrations.models import ImmichIntegration
import uuid
import requests

class AdventureImageViewSet(viewsets.ModelViewSet):
    serializer_class = AdventureImageSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def image_delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def toggle_primary(self, request, *args, **kwargs):
        # Makes the image the primary image for the adventure, if there is already a primary image linked to the adventure, it is set to false and the new image is set to true. make sure that the permission is set to the owner of the adventure
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        
        instance = self.get_object()
        adventure = instance.adventure
        if adventure.user_id != request.user:
            return Response({"error": "User does not own this adventure"}, status=status.HTTP_403_FORBIDDEN)
        
        # Check if the image is already the primary image
        if instance.is_primary:
            return Response({"error": "Image is already the primary image"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Set the current primary image to false
        AdventureImage.objects.filter(adventure=adventure, is_primary=True).update(is_primary=False)

        # Set the new image to true
        instance.is_primary = True
        instance.save()
        return Response({"success": "Image set as primary image"})

    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        adventure_id = request.data.get('adventure')
        try:
            adventure = Adventure.objects.get(id=adventure_id)
        except Adventure.DoesNotExist:
            return Response({"error": "Adventure not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if adventure.user_id != request.user:
            # Check if the adventure has any collections
            if adventure.collections.exists():
                # Check if the user is in the shared_with list of any of the adventure's collections
                user_has_access = False
                for collection in adventure.collections.all():
                    if collection.shared_with.filter(id=request.user.id).exists():
                        user_has_access = True
                        break
                
                if not user_has_access:
                    return Response({"error": "User does not have permission to access this adventure"}, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({"error": "User does not own this adventure"}, status=status.HTTP_403_FORBIDDEN)
        
        # Handle Immich ID for shared users by downloading the image
        if (request.user != adventure.user_id and 
            'immich_id' in request.data and 
            request.data.get('immich_id')):
            
            immich_id = request.data.get('immich_id')
            
            # Get the shared user's Immich integration
            try:
                user_integration = ImmichIntegration.objects.get(user_id=request.user)
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
                content_type = immich_response.headers.get('Content-Type', 'image/jpeg')
                if not content_type.startswith('image/'):
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
                file_ext = ext_map.get(content_type, '.jpg')
                filename = f"immich_{immich_id}{file_ext}"
                
                # Create a Django ContentFile from the downloaded image
                image_file = ContentFile(immich_response.content, name=filename)
                
                # Modify request data to use the downloaded image instead of immich_id
                request_data = request.data.copy()
                request_data.pop('immich_id', None)  # Remove immich_id
                request_data['image'] = image_file  # Add the image file
                
                # Create the serializer with the modified data
                serializer = self.get_serializer(data=request_data)
                serializer.is_valid(raise_exception=True)
                
                # Save with the downloaded image
                adventure = serializer.validated_data['adventure']
                serializer.save(user_id=adventure.user_id, image=image_file)
                
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
        
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        
        adventure_id = request.data.get('adventure')
        try:
            adventure = Adventure.objects.get(id=adventure_id)
        except Adventure.DoesNotExist:
            return Response({"error": "Adventure not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if adventure.user_id != request.user:
            return Response({"error": "User does not own this adventure"}, status=status.HTTP_403_FORBIDDEN)
        
        return super().update(request, *args, **kwargs)
    
    def perform_destroy(self, instance):
        print("perform_destroy")
        return super().perform_destroy(instance)

    def destroy(self, request, *args, **kwargs):
        print("destroy")
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        
        instance = self.get_object()
        adventure = instance.adventure
        if adventure.user_id != request.user:
            return Response({"error": "User does not own this adventure"}, status=status.HTTP_403_FORBIDDEN)
        
        return super().destroy(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        
        instance = self.get_object()
        adventure = instance.adventure
        if adventure.user_id != request.user:
            return Response({"error": "User does not own this adventure"}, status=status.HTTP_403_FORBIDDEN)
        
        return super().partial_update(request, *args, **kwargs)
    
    @action(detail=False, methods=['GET'], url_path='(?P<adventure_id>[0-9a-f-]+)')
    def adventure_images(self, request, adventure_id=None, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            adventure_uuid = uuid.UUID(adventure_id)
        except ValueError:
            return Response({"error": "Invalid adventure ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Updated queryset to include images from adventures the user owns OR has shared access to
        queryset = AdventureImage.objects.filter(
            Q(adventure__id=adventure_uuid) & (
                Q(adventure__user_id=request.user) |  # User owns the adventure
                Q(adventure__collections__shared_with=request.user)  # User has shared access via collection
            )
        ).distinct()
        
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    def get_queryset(self):
        # Updated to include images from adventures the user owns OR has shared access to
        return AdventureImage.objects.filter(
            Q(adventure__user_id=self.request.user) |  # User owns the adventure
            Q(adventure__collections__shared_with=self.request.user)  # User has shared access via collection
        ).distinct()

    def perform_create(self, serializer):
        # Always set the image owner to the adventure owner, not the current user
        adventure = serializer.validated_data['adventure']
        serializer.save(user_id=adventure.user_id)