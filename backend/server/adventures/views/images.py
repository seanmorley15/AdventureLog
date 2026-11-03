from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from adventures.throttling import ImageImportThrottle, ImageProxyThrottle
from django.http import HttpResponse
from django.db.models import Q
from django.core.files.base import ContentFile
from django.contrib.contenttypes.models import ContentType
from adventures.models import (
    Activity,
    Collection,
    CollectionItineraryDay,
    Location,
    Transportation,
    Note,
    Lodging,
    Visit,
    ContentImage,
    Trail,
)
from adventures.serializers import ContentImageSerializer, ImageMapPinSerializer
from adventures.serializers.media import (
    ImageFetchSerializer,
    ImageImportFromUrlsSerializer,
    ImageImportResultSerializer,
    ImageUploadSerializer,
)
from integrations.facade import ImmichIntegration, immich_integration_for
from adventures.views.mixins import ContentObjectMixin
from adventures.permissions import ContentImagePermission
import logging
import requests
from adventures.services.media_quota import ensure_media_storage_available, get_uploaded_file_size
from core.exceptions import APIError
from core.serializers import validated

from adventures.services.images.fetch import (
    download_remote_image,
    import_remote_images_for_object,
)
from adventures.services.images.metadata import (
    ImageSource,
    create_content_image,
    fetch_immich_coordinates,
)

logger = logging.getLogger(__name__)

@extend_schema_view(
    list=extend_schema(description='Every image you can see: on your records and on records in collections you belong to.'),
    update=extend_schema(description='Change `is_primary` or the image file.'),
    partial_update=extend_schema(description='Change `is_primary` or the image file.'),
)
class ContentImageViewSet(ContentObjectMixin, viewsets.ModelViewSet):
    """
    Images on locations, visits, lodging, transportation, notes, trip days, activities and trails.

    An image belongs to the owner of the record it is on. Photos taken with a location in their
    metadata get coordinates and appear on the map. Images can also point at an Immich photo.
    """

    openapi_tags = ['Media']
    queryset = ContentImage.objects.all()
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    content_object_models = {
        'location': Location,
        'transportation': Transportation,
        'note': Note,
        'lodging': Lodging,
        'visit': Visit,
        'collectionitineraryday': CollectionItineraryDay,
        'activity': Activity,
        'trail': Trail,
    }
    validate_object_uuid = True

    serializer_class = ContentImageSerializer
    permission_classes = [ContentImagePermission]

    def get_queryset(self):
        """Get all images the user has access to"""
        if getattr(self, 'swagger_fake_view', False) or not self.request.user.is_authenticated:
            return ContentImage.objects.none()
        
        # Import here to avoid circular imports
        from adventures.models import Activity, CollectionItineraryDay, Location, Transportation, Note, Lodging, Trail, Visit
        
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
            ) |
            (
                Q(content_type=ContentType.objects.get_for_model(CollectionItineraryDay)) &
                Q(object_id__in=CollectionItineraryDay.objects.filter(
                    Q(collection__user=self.request.user) | Q(collection__shared_with=self.request.user)
                ).values_list('id', flat=True))
            ) |
            (
                Q(content_type=ContentType.objects.get_for_model(Activity)) &
                Q(object_id__in=Activity.objects.filter(
                    Q(day__collection__user=self.request.user)
                    | Q(day__collection__shared_with=self.request.user)
                    | Q(collection__user=self.request.user)
                    | Q(collection__shared_with=self.request.user)
                ).values_list('id', flat=True))
            ) |
            (
                Q(content_type=ContentType.objects.get_for_model(Trail)) &
                Q(object_id__in=Trail.objects.filter(
                    Q(day__collection__user=self.request.user)
                    | Q(day__collection__shared_with=self.request.user)
                    | Q(collection__user=self.request.user)
                    | Q(collection__shared_with=self.request.user)
                ).values_list('id', flat=True))
            ) |
            (
                Q(content_type=ContentType.objects.get_for_model(Collection)) &
                Q(object_id__in=Collection.objects.filter(
                    Q(user=self.request.user) | Q(shared_with=self.request.user)
                ).values_list('id', flat=True))
            )
        ).distinct()

    @extend_schema(request=None, responses=ContentImageSerializer)
    @action(detail=True, methods=['post'], url_path='toggle-primary')
    def toggle_primary(self, request, *args, **kwargs):
        """
        Make an image the primary one

        The primary image is the cover of its record. The record's other images stop being
        primary. Answers 400 `already_primary` when it already is.
        """
        instance = self.get_object()

        if instance.is_primary:
            raise APIError('This image is already the primary image.', code='already_primary')

        # Set other images of the same content object to not primary
        ContentImage.objects.filter(
            content_type=instance.content_type,
            object_id=instance.object_id,
            is_primary=True
        ).update(is_primary=False)

        # Set the new image to primary
        instance.is_primary = True
        instance.save()
        return Response(self.get_serializer(instance).data)

    @extend_schema(responses=ImageMapPinSerializer(many=True))
    @action(detail=False, methods=['get'], url_path='map-pins')
    def map_pins(self, request):
        """
        List geotagged images

        Images you can see that have coordinates, for showing on a map.
        """
        images = (
            self.get_queryset()
            .filter(coordinates__isnull=False)
            .select_related('content_type', 'user')
            .prefetch_related('content_object')
            .order_by('-is_primary', 'id')
        )

        pins = []
        context = {'request': request}
        for image in images.iterator(chunk_size=200):
            data = ImageMapPinSerializer(image, context=context).to_representation(image)
            if data:
                pins.append(data)

        return Response(pins)

    @extend_schema(
        request=ImageFetchSerializer,
        responses={
            (200, 'image/*'): OpenApiResponse(response=bytes, description='The image, as the remote server sent it.'),
            502: OpenApiResponse(description='The remote server failed (`upstream_error`).'),
            504: OpenApiResponse(description='The remote server was too slow (`upstream_timeout`).'),
        },
    )
    @action(
        detail=False, methods=['post'], url_path='fetch-from-url',
        permission_classes=[IsAuthenticated], throttle_classes=[ImageProxyThrottle],
    )
    def fetch_from_url(self, request):
        """
        Fetch a remote image

        Downloads an image from a public web address and returns its bytes, so the browser can
        use pictures from servers that do not allow cross-site requests. Only public internet
        addresses are fetched.
        """
        image_url = validated(ImageFetchSerializer, request.data)['url']
        try:
            image_data = download_remote_image(str(image_url).strip())
        except ValueError:
            raise APIError('That is not a usable image address.', code='invalid')
        except requests.exceptions.Timeout:
            logger.error("Timeout fetching image from URL %s", image_url)
            raise APIError('The image took too long to download.', code='upstream_timeout', status=504)
        except requests.exceptions.RequestException as e:
            logger.error("Failed to fetch image from URL %s: %s", image_url, str(e))
            raise APIError('The image could not be downloaded.', code='upstream_error', status=502)
        return HttpResponse(image_data['content'], content_type=image_data['content_type'], status=200)

    @extend_schema(
        request=ImageImportFromUrlsSerializer,
        responses={
            201: OpenApiResponse(ImageImportResultSerializer, description='Every image was imported.'),
            200: OpenApiResponse(ImageImportResultSerializer, description='Some images were imported; see `results`.'),
            400: OpenApiResponse(description='None could be imported (`import_failed`, with `results`), or invalid input.'),
        },
    )
    @action(
        detail=False, methods=['post'], url_path='import-from-urls',
        permission_classes=[IsAuthenticated], throttle_classes=[ImageImportThrottle],
    )
    def import_from_urls(self, request):
        """
        Import images from web addresses

        Downloads up to 10 images and attaches them to a record, for example pictures from
        `GET /api/places/images/` or a place search. Each address gets its own entry in
        `results`.
        """
        params = validated(ImageImportFromUrlsSerializer, request.data)
        urls = [str(url).strip() for url in params['urls'] if str(url).strip()]
        content_object = self._get_and_validate_content_object(params['content_type'], params['object_id'])

        owner = self._content_owner(content_object, request.user)

        explicit_source = params.get('source')
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
            raise APIError('None of the images could be imported.', code='import_failed', results=results)

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

    @extend_schema(
        request={'multipart/form-data': ImageUploadSerializer, 'application/json': ImageUploadSerializer},
        responses={
            201: ContentImageSerializer,
            413: OpenApiResponse(description='The file would exceed the owner\'s media storage (`media_quota_exceeded`).'),
            502: OpenApiResponse(description='The Immich photo could not be fetched (`immich_fetch_failed`).'),
        },
    )
    def create(self, request, *args, **kwargs):
        """
        Add an image

        Upload a file as `image` (multipart), or link a photo from your Immich server with
        `immich_id`. The image belongs to the owner of the record it is added to.
        """
        params = validated(ImageUploadSerializer, request.data)
        content_type_name = params['content_type']
        object_id = params['object_id']
        content_object = self._get_and_validate_content_object(content_type_name, object_id)

        content_type = ContentType.objects.get_for_model(content_object.__class__)
        
        # Handle Immich ID for shared users by downloading the image
        if (hasattr(content_object, 'user') and 
            request.user != content_object.user and 
            'immich_id' in request.data and 
            request.data.get('immich_id')):
            
            return self._handle_immich_image_creation(request, content_object, content_type, object_id)
        
        # Standard image creation
        return self._create_standard_image(request, content_object, content_type, object_id)
    
    def _content_owner(self, content_object, fallback):
        """Day photos belong to the collection owner, the same way lodging does."""
        from adventures.services.day_plan.files import activity_collection, trail_collection

        if isinstance(content_object, CollectionItineraryDay):
            return content_object.collection.user
        if isinstance(content_object, Activity):
            parent = activity_collection(content_object)
            if parent is not None:
                return parent.user
        if isinstance(content_object, Trail):
            parent = trail_collection(content_object)
            if parent is not None:
                return parent.user
        return getattr(content_object, 'user', fallback)
    
    def _handle_immich_image_creation(self, request, content_object, content_type, object_id):
        """Handle creation of image from Immich for shared users"""
        immich_id = request.data.get('immich_id')
        
        # Get the shared user's Immich integration
        try:
            user_integration = ImmichIntegration.objects.get(user=request.user)
        except ImmichIntegration.DoesNotExist:
            raise APIError(
                'No Immich integration found for your account. Please set up Immich integration first.',
                code='immich_integration_not_found',
            )
        
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
                raise APIError('Immich did not return an image.', code='invalid_content_type', status=502)
            
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
            ensure_media_storage_available(owner, get_uploaded_file_size(image_file))

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
            raise APIError('The photo could not be fetched from Immich.', code='immich_fetch_failed', status=502)
    
    def _create_standard_image(self, request, content_object, content_type, object_id):
        """Handle standard image creation without deepcopy issues"""

        image_file = request.FILES.get('image')
        immich_id = request.data.get('immich_id')

        if not image_file and not immich_id:
            raise APIError('Send an image file or an immich_id.', code='invalid')

        owner = self._content_owner(content_object, request.user)
        explicit_source = request.data.get('source')
        source_url = request.data.get('source_url')

        coordinates = None
        immich_integration = None

        if image_file:
            ensure_media_storage_available(owner, get_uploaded_file_size(image_file))

            file_bytes = image_file.read()
            image_file = ContentFile(file_bytes, name=image_file.name)

            if immich_id:
                immich_integration = immich_integration_for(owner)
                coordinates = fetch_immich_coordinates(immich_integration, immich_id)
                immich_id = None
        else:
            file_bytes = None
            immich_integration = immich_integration_for(owner)

        image = create_content_image(
            user=owner,
            content_type=content_type,
            object_id=object_id,
            image_file=image_file,
            immich_id=immich_id or None,
            file_bytes=file_bytes,
            source_url=source_url,
            explicit_source=explicit_source,
            immich_integration=immich_integration,
            coordinates=coordinates,
        )

        serializer = self.get_serializer(image)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    
    def perform_create(self, serializer):
        # The content_type and object_id are already set in the create method
        # Just ensure the user is set correctly
        pass