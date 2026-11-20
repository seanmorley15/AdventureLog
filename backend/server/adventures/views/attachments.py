from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from adventures.models import ContentAttachment, Location, Lodging, Note, Transportation, Visit
from adventures.permissions import ContentImagePermission
from adventures.serializers import AttachmentSerializer
from adventures.serializers.media import AttachmentTargetSerializer, AttachmentUploadSerializer
from adventures.services.media_quota import ensure_media_storage_available, get_uploaded_file_size
from adventures.views.mixins import ContentObjectMixin
from core.serializers import validated

_QUOTA = OpenApiResponse(description="The file would exceed the owner's media storage (`media_quota_exceeded`).")


@extend_schema_view(
    create=extend_schema(
        summary='Add an attachment',
        description='Upload a file (multipart) to a location, visit, lodging, transportation or note. The file '
        'belongs to the owner of the record. GPX files get a `geojson` track for maps.',
        request={'multipart/form-data': AttachmentUploadSerializer},
        responses={201: AttachmentSerializer, 413: _QUOTA},
    ),
    update=extend_schema(responses={200: AttachmentSerializer, 413: _QUOTA}),
    partial_update=extend_schema(description='Rename it with `name`, or replace the `file`.',
                                 responses={200: AttachmentSerializer, 413: _QUOTA}),
)
class AttachmentViewSet(ContentObjectMixin, viewsets.ModelViewSet):
    """Files (PDFs, tickets, GPX tracks…) on locations, visits, lodging, transportation and notes."""

    openapi_tags = ['Media']
    queryset = ContentAttachment.objects.all()
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = AttachmentSerializer
    content_object_models = {
        'location': Location,
        'transportation': Transportation,
        'note': Note,
        'lodging': Lodging,
        'visit': Visit,
    }
    permission_classes = [ContentImagePermission]

    def get_queryset(self):
        """Get all images the user has access to"""
        if getattr(self, 'swagger_fake_view', False) or not self.request.user.is_authenticated:
            return ContentAttachment.objects.none()

        
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
        # The record first: a missing or forbidden record is a 404 or 403 whatever the file.
        params = validated(AttachmentTargetSerializer, request.data)
        self._content_object = self._get_and_validate_content_object(params['content_type'], params['object_id'])
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        content_object = self._content_object
        attachment_user = self._get_attachment_user(content_object)
        ensure_media_storage_available(attachment_user, get_uploaded_file_size(serializer.validated_data.get('file')))
        serializer.save(
            user=attachment_user,
            content_type=ContentType.objects.get_for_model(type(content_object)),
            object_id=content_object.id,
        )

    def perform_update(self, serializer):
        upload_file = serializer.validated_data.get('file')
        if upload_file:
            # The new file replaces the old one, so the old one stops counting.
            old_name = serializer.instance.file.name if serializer.instance.file else None
            ensure_media_storage_available(
                serializer.instance.user, get_uploaded_file_size(upload_file), exclude_names=[old_name]
            )
        serializer.save()

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