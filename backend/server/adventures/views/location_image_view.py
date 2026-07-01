from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from adventures.throttling import ImageImportThrottle, ImageProxyThrottle
from django.http import HttpResponse
from django.db.models import Q
from django.core.files.base import ContentFile
from django.contrib.contenttypes.models import ContentType
from adventures.models import Location, Transportation, Note, Lodging, Visit, ContentImage
from adventures.serializers import ContentImageSerializer, ImageMapPinSerializer
from integrations.models import ImmichIntegration
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from adventures.permissions import ContentImagePermission
import logging
import requests
from users.media_utils import enforce_media_storage_limit, get_uploaded_file_size

from adventures.services.images.fetch import (
    download_remote_image,
    import_remote_images_for_object,
)
from adventures.services.images.metadata import ImageSource, create_content_image

logger = logging.getLogger(__name__)

class ContentImageViewSet(viewsets.ModelViewSet):
    serializer_class = ContentImageSerializer
    permission_classes = [ContentImagePermission]

    def get_queryset(self):
        """Get all images the user has access to"""
        if not self.request.user.is_authenticated:
            return ContentImage.objects.none()
        
        # Import here to avoid circular imports
        from adventures.models import Location, Transportation, Note, Lodging, Visit
        
        # Build a single query with all conditions
        return ContentImage.objects.filter(
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

    @action(detail=True, methods=['post'])
    def image_delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def toggle_primary(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Check if the image is already the primary image
        if instance.is_primary:
            return Response(
                {"error": "Image is already the primary image"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
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

    @action(detail=False, methods=['get'], url_path='map_pins')
    def map_pins(self, request):
        """Return geotagged images accessible to the current user for map display."""
        images = (
            self.get_queryset()
            .filter(coordinates__isnull=False)
            .select_related('content_type', 'user')
            .order_by('-is_primary', 'id')
        )

        pins = []
        for image in images.iterator(chunk_size=200):
            data = ImageMapPinSerializer(image, context={'request': request}).data
            if data:
                pins.append(data)

        return Response(pins)

    @action(detail=False, methods=['post'],
            permission_classes=[IsAuthenticated],
            throttle_classes=[ImageProxyThrottle])
    def fetch_from_url(self, request):
        """
        Authenticated proxy endpoint to fetch images from external URLs.
        Avoids CORS issues when the frontend downloads images from third-party
        servers (e.g. wikimedia.org). Requires a logged-in user and is
        rate-limited to 60 requests/minute.
        """
        image_url = request.data.get('url')
        if not image_url:
            return Response(
                {"error": "URL is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            image_data = download_remote_image(str(image_url).strip())
            return HttpResponse(image_data['content'], content_type=image_data['content_type'], status=200)

        except ValueError:
            return Response({"error": "Invalid image URL"}, status=status.HTTP_400_BAD_REQUEST)

        except requests.exceptions.Timeout:
            logger.error("Timeout fetching image from URL %s", image_url)
            return Response(
                {"error": "Download timeout - image may be too large or server too slow"},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
        except requests.exceptions.RequestException as e:
            logger.error("Failed to fetch image from URL %s: %s", image_url, str(e))
            return Response(
                {"error": "Failed to fetch image from the remote server"},
                status=status.HTTP_502_BAD_GATEWAY
            )

    @action(
        detail=False,
        methods=['post'],
        permission_classes=[IsAuthenticated],
        throttle_classes=[ImageImportThrottle],
    )
    def import_from_urls(self, request):
        content_type_name = request.data.get('content_type')
        object_id = request.data.get('object_id')
        urls = request.data.get('urls')

        if not isinstance(urls, list) or not urls:
            return Response({"error": "urls must be a non-empty array"}, status=status.HTTP_400_BAD_REQUEST)

        urls = [str(url).strip() for url in urls if str(url).strip()]
        if not urls:
            return Response({"error": "No valid URLs provided"}, status=status.HTTP_400_BAD_REQUEST)

        if len(urls) > 10:
            return Response({"error": "Maximum 10 URLs per request"}, status=status.HTTP_400_BAD_REQUEST)

        content_object = self._get_and_validate_content_object(content_type_name, object_id)
        if isinstance(content_object, Response):
            return content_object

        owner = getattr(content_object, 'user', request.user)

        explicit_source = request.data.get('source')
        import_summary = import_remote_images_for_object(
            content_object,
            urls,
            owner=owner,
            max_workers=min(5, len(urls)),
            explicit_source=explicit_source,
        )

        created_images = import_summary['created_images']
        results = import_summary['results']

        if not created_images:
            return Response(
                {
                    'error': 'No images could be imported',
                    'results': results,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serialized = ContentImageSerializer(created_images, many=True, context={'request': request})
        response_status = (
            status.HTTP_201_CREATED
            if import_summary['created_count'] == import_summary['requested_count']
            else status.HTTP_200_OK
        )

        return Response(
            {
                'created': serialized.data,
                'results': results,
                'created_count': import_summary['created_count'],
                'requested_count': import_summary['requested_count'],
            },
            status=response_status,
        )

    def create(self, request, *args, **kwargs):
        # Get content type and object ID from request
        content_type_name = request.data.get('content_type')
        object_id = request.data.get('object_id')
        
        if not content_type_name or not object_id:
            return Response({
                "error": "content_type and object_id are required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the content object and validate permissions
        content_object = self._get_and_validate_content_object(content_type_name, object_id)
        if isinstance(content_object, Response):  # Error response
            return content_object
        
        content_type = ContentType.objects.get_for_model(content_object.__class__)
        
        # Handle Immich ID for shared users by downloading the image
        if (hasattr(content_object, 'user') and 
            request.user != content_object.user and 
            'immich_id' in request.data and 
            request.data.get('immich_id')):
            
            return self._handle_immich_image_creation(request, content_object, content_type, object_id)
        
        # Standard image creation
        return self._create_standard_image(request, content_object, content_type, object_id)
    
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
        
        # Validate object_id format (must be a valid UUID, not "undefined" or empty)
        if not object_id or object_id == 'undefined':
            return Response({
                "error": "object_id is required and must be a valid UUID"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        import uuid as uuid_module
        try:
            uuid_module.UUID(str(object_id))
        except (ValueError, AttributeError):
            return Response({
                "error": f"Invalid object_id format: {object_id}"
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
    
    def _handle_immich_image_creation(self, request, content_object, content_type, object_id):
        """Handle creation of image from Immich for shared users"""
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

            owner = content_object.user if hasattr(content_object, 'user') else request.user
            allowed, details = enforce_media_storage_limit(
                owner,
                get_uploaded_file_size(image_file),
            )
            if not allowed:
                return Response(
                    {
                        "error": "Media storage limit exceeded",
                        **details,
                    },
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )

            image = create_content_image(
                user=owner,
                content_type=content_type,
                object_id=object_id,
                image_file=image_file,
                file_bytes=immich_response.content,
                explicit_source=ImageSource.IMMICH,
            )
            serializer = self.get_serializer(image)
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
    
    def _create_standard_image(self, request, content_object, content_type, object_id):
        """Handle standard image creation without deepcopy issues"""

        image_file = request.FILES.get('image')
        immich_id = request.data.get('immich_id')

        if not image_file and not immich_id:
            return Response({"error": "No image uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        owner = getattr(content_object, 'user', request.user)
        explicit_source = request.data.get('source')
        source_url = request.data.get('source_url')

        if image_file:
            allowed, details = enforce_media_storage_limit(
                owner,
                get_uploaded_file_size(image_file),
            )
            if not allowed:
                return Response(
                    {
                        "error": "Media storage limit exceeded",
                        **details,
                    },
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )

            file_bytes = image_file.read()
            image_file = ContentFile(file_bytes, name=image_file.name)
            immich_integration = None
        else:
            file_bytes = None
            immich_integration = ImmichIntegration.objects.filter(user=owner).first()

        image = create_content_image(
            user=owner,
            content_type=content_type,
            object_id=object_id,
            image_file=image_file if not immich_id else None,
            immich_id=immich_id or None,
            file_bytes=file_bytes,
            source_url=source_url,
            explicit_source=explicit_source,
            immich_integration=immich_integration,
        )

        serializer = self.get_serializer(image)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    
    def perform_create(self, serializer):
        # The content_type and object_id are already set in the create method
        # Just ensure the user is set correctly
        pass