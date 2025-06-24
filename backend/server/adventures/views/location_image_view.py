from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from django.core.files.base import ContentFile
from adventures.models import Location, LocationImage
from adventures.serializers import LocationImageSerializer
from integrations.models import ImmichIntegration
import uuid
import requests
import os

class AdventureImageViewSet(viewsets.ModelViewSet):
    serializer_class = LocationImageSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def image_delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def toggle_primary(self, request, *args, **kwargs):
        # Makes the image the primary image for the location, if there is already a primary image linked to the location, it is set to false and the new image is set to true. make sure that the permission is set to the owner of the location
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        
        instance = self.get_object()
        location = instance.location
        if location.user != request.user:
            return Response({"error": "User does not own this location"}, status=status.HTTP_403_FORBIDDEN)
        
        # Check if the image is already the primary image
        if instance.is_primary:
            return Response({"error": "Image is already the primary image"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Set the current primary image to false
        LocationImage.objects.filter(location=location, is_primary=True).update(is_primary=False)

        # Set the new image to true
        instance.is_primary = True
        instance.save()
        return Response({"success": "Image set as primary image"})

    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        location_id = request.data.get('location')
        try:
            location = Location.objects.get(id=location_id)
        except Location.DoesNotExist:
            return Response({"error": "location not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if location.user != request.user:
            # Check if the location has any collections
            if location.collections.exists():
                # Check if the user is in the shared_with list of any of the location's collections
                user_has_access = False
                for collection in location.collections.all():
                    if collection.shared_with.filter(id=request.user.id).exists():
                        user_has_access = True
                        break
                
                if not user_has_access:
                    return Response({"error": "User does not have permission to access this location"}, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({"error": "User does not own this location"}, status=status.HTTP_403_FORBIDDEN)
        
        # Handle Immich ID for shared users by downloading the image
        if (request.user != location.user and 
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
                location = serializer.validated_data['location']
                serializer.save(user=location.user, image=image_file)
                
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
        
        location_id = request.data.get('location')
        try:
            location = Location.objects.get(id=location_id)
        except Location.DoesNotExist:
            return Response({"error": "location not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if location.user != request.user:
            return Response({"error": "User does not own this location"}, status=status.HTTP_403_FORBIDDEN)
        
        return super().update(request, *args, **kwargs)
    
    def perform_destroy(self, instance):
        return super().perform_destroy(instance)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        
        instance = self.get_object()
        location = instance.location
        if location.user != request.user:
            return Response({"error": "User does not own this location"}, status=status.HTTP_403_FORBIDDEN)
        
        return super().destroy(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        
        instance = self.get_object()
        location = instance.location
        if location.user != request.user:
            return Response({"error": "User does not own this location"}, status=status.HTTP_403_FORBIDDEN)
        
        return super().partial_update(request, *args, **kwargs)
    
    @action(detail=False, methods=['GET'], url_path='(?P<location_id>[0-9a-f-]+)')
    def location_images(self, request, location_id=None, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            location_uuid = uuid.UUID(location_id)
        except ValueError:
            return Response({"error": "Invalid location ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Updated queryset to include images from locations the user owns OR has shared access to
        queryset = LocationImage.objects.filter(
            Q(location__id=location_uuid) & (
                Q(location__user=request.user) |  # User owns the location
                Q(location__collections__shared_with=request.user)  # User has shared access via collection
            )
        ).distinct()
        
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    def get_queryset(self):
        # Updated to include images from locations the user owns OR has shared access to
        return LocationImage.objects.filter(
            Q(location__user=self.request.user) |  # User owns the location
            Q(location__collections__shared_with=self.request.user)  # User has shared access via collection
        ).distinct()

    def perform_create(self, serializer):
        # Always set the image owner to the location owner, not the current user
        location = serializer.validated_data['location']
        serializer.save(user=location.user)