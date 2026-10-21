"""Photos and files, and the mixin that puts them on other records."""

from adventures.models import ContentImage, ContentAttachment
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from core.serializers import CustomModelSerializer
from core.public_url import build_media_url, get_public_url
from integrations.facade import immich_integration_for
from adventures.utils.geojson import cached_gpx_geojson
from core.geo import point_to_lat_lon
from adventures.serializers.geo_fields import CoordinateSerializerMixin

def _immich_integration_for(context, user_id):
    """A user's Immich integration, looked up once per request however many photos need it."""
    cache = context.setdefault('_immich_integrations', {})
    if user_id not in cache:
        cache[user_id] = immich_integration_for(user_id)
    return cache[user_id]


class ContentImageSerializer(CoordinateSerializerMixin, CustomModelSerializer):
    source = serializers.ChoiceField(choices=ContentImage.Source.choices, read_only=True)
    source_url = serializers.URLField(read_only=True)

    class Meta:
        model = ContentImage
        fields = [
            'id', 'image', 'is_primary', 'user', 'immich_id',
            'source', 'source_url', 'latitude', 'longitude',
        ]
        # Where an image comes from is fixed when it is created (see
        # ContentImageViewSet.create). Letting a later PATCH change it would let an
        # editor point a shared image at any asset in the owner's Immich library.
        read_only_fields = ['id', 'user', 'image', 'immich_id', 'source', 'source_url']

    def _get_immich_integration(self, user_id):
        """Cache Immich integrations per request to avoid N+1 lookups."""
        return _immich_integration_for(self.context, user_id)

    def to_representation(self, instance):
        # If immich_id is set, check for user integration once
        integration = None
        if instance.immich_id:
            integration = self._get_immich_integration(instance.user_id)
            if not integration:
                return None  # Skip if Immich image but no integration

        # Base representation
        representation = super().to_representation(instance)

        # Prepare public URL once
        public_url = get_public_url()

        if instance.immich_id:
            # Use Immich integration URL
            representation['image'] = f"{public_url}/api/integrations/immich/assets/{integration.id}/{instance.immich_id}/"
        elif instance.image:
            # Use local image URL
            representation['image'] = build_media_url(instance.image.name)

        return representation


class ImageMapPinSerializer(serializers.ModelSerializer):
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    parent_type = serializers.SerializerMethodField()
    parent_id = serializers.SerializerMethodField()
    parent_name = serializers.SerializerMethodField()

    class Meta:
        model = ContentImage
        fields = [
            'id',
            'image',
            'latitude',
            'longitude',
            'source',
            'is_primary',
            'parent_type',
            'parent_id',
            'parent_name',
        ]

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_latitude(self, obj):
        lat, _ = point_to_lat_lon(obj.coordinates)
        return lat

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_longitude(self, obj):
        _, lon = point_to_lat_lon(obj.coordinates)
        return lon

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_image(self, obj):
        if obj.immich_id:
            integration = _immich_integration_for(self.context, obj.user_id)
            if not integration:
                return None
            public_url = get_public_url()
            return f"{public_url}/api/integrations/immich/assets/{integration.id}/{obj.immich_id}/"
        if obj.image:
            return build_media_url(obj.image.name)
        return None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_parent_type(self, obj):
        return obj.content_type.model if obj.content_type_id else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_parent_id(self, obj):
        return str(obj.object_id)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_parent_name(self, obj):
        parent = obj.content_object
        return getattr(parent, 'name', None) if parent else None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation.get('image') is None:
            return {}
        if representation.get('latitude') is None or representation.get('longitude') is None:
            return {}
        return representation


class AttachmentSerializer(CustomModelSerializer):
    extension = serializers.SerializerMethodField()
    geojson = serializers.SerializerMethodField()
    class Meta:
        model = ContentAttachment
        fields = ['id', 'file', 'extension', 'name', 'user', 'geojson']
        read_only_fields = ['id', 'user']

    @extend_schema_field(serializers.CharField())
    def get_extension(self, obj):
        return obj.file.name.split('.')[-1]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.file:
            representation['file'] = build_media_url(instance.file.name)
        return representation

    @extend_schema_field(serializers.JSONField(allow_null=True))
    def get_geojson(self, obj):
        # The story payload never carries attachment GeoJSON, so skip the work.
        if self.context.get('story'):
            return None
        if obj.file and obj.file.name.endswith('.gpx'):
            return cached_gpx_geojson(obj.file)
        return None


class MediaFieldsMixin:
    """The ``images`` and ``attachments`` fields of records that carry photos and files."""

    @extend_schema_field(ContentImageSerializer(many=True))
    def get_images(self, obj):
        serializer = ContentImageSerializer(obj.images.all(), many=True, context=self.context)
        # Filter out None values from the serialized data
        return [image for image in serializer.data if image is not None]

    @extend_schema_field(AttachmentSerializer(many=True))
    def get_attachments(self, obj):
        serializer = AttachmentSerializer(obj.attachments.all(), many=True, context=self.context)
        # Filter out None values from the serialized data
        return [attachment for attachment in serializer.data if attachment is not None]


# --- Requests and responses of the image and attachment endpoints ------------------------

IMAGE_CONTENT_TYPES = [
    'location', 'transportation', 'note', 'lodging', 'visit', 'collectionitineraryday', 'activity', 'trail',
]
ATTACHMENT_CONTENT_TYPES = ['location', 'transportation', 'note', 'lodging', 'visit']


class ImageUploadSerializer(serializers.Serializer):
    content_type = serializers.ChoiceField(choices=IMAGE_CONTENT_TYPES, help_text='The kind of record.')
    object_id = serializers.UUIDField(help_text='The record id.')
    image = serializers.ImageField(required=False, help_text='The file. Send this or `immich_id`.')
    immich_id = serializers.CharField(required=False, help_text='An Immich asset id to link instead of a file.')
    source = serializers.CharField(required=False, help_text='Where the image came from, e.g. `upload`, `google`.')
    source_url = serializers.URLField(required=False, help_text='The page or file it was taken from.')


class ImageFetchSerializer(serializers.Serializer):
    url = serializers.URLField(help_text='A public http(s) address of an image.')


class ImageImportFromUrlsSerializer(serializers.Serializer):
    content_type = serializers.ChoiceField(choices=IMAGE_CONTENT_TYPES)
    object_id = serializers.UUIDField()
    urls = serializers.ListField(child=serializers.URLField(), min_length=1, max_length=10)
    source = serializers.CharField(required=False, help_text='e.g. `google` or `wikipedia`.')


class ImageImportItemSerializer(serializers.Serializer):
    url = serializers.CharField()
    status = serializers.ChoiceField(choices=['created', 'failed'])
    id = serializers.UUIDField(required=False, help_text='The new image, when created.')
    error = serializers.CharField(required=False, help_text='Why it failed.')


class ImageImportResultSerializer(serializers.Serializer):
    created = ContentImageSerializer(many=True)
    results = ImageImportItemSerializer(many=True)
    created_count = serializers.IntegerField()
    requested_count = serializers.IntegerField()


class AttachmentTargetSerializer(serializers.Serializer):
    content_type = serializers.ChoiceField(choices=ATTACHMENT_CONTENT_TYPES, help_text='The kind of record.')
    object_id = serializers.UUIDField(help_text='The record id.')


class AttachmentUploadSerializer(AttachmentTargetSerializer):
    file = serializers.FileField(help_text='Any file; GPX tracks are drawn on maps.')
    name = serializers.CharField(required=False, allow_blank=True, help_text='A label. Defaults to empty.')
