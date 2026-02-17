"""
Serializer mixins for common patterns across Location, Transportation, Lodging, etc.
"""


class OwnershipSerializerMixin:
    """
    Mixin providing get_is_owned() and get_is_owner() for serializers.

    Both methods check if the requesting user owns the serialized object.
    get_is_owned is used by entity serializers (Location, Transportation, etc.)
    get_is_owner is used by media serializers (ContentImage, ContentAttachment)

    Used by: CategorySerializer, LocationSerializer, MapPinSerializer,
             LodgingMapPinSerializer, TransportationMapPinSerializer,
             UltraSlimCollectionSerializer, ContentImageSerializer, AttachmentSerializer
    """

    def _check_ownership(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return obj.user == request.user
        return False

    def get_is_owned(self, obj):
        return self._check_ownership(obj)

    def get_is_owner(self, obj):
        return self._check_ownership(obj)


class MediaSerializerMixin:
    """
    Mixin providing get_images() and get_attachments() for entity serializers.

    Filters out soft-deleted items and None values.

    Used by: LocationSerializer, TransportationSerializer, LodgingSerializer
    """

    def get_images(self, obj):
        from adventures.serializers import ContentImageSerializer
        serializer = ContentImageSerializer(obj.images.filter(is_deleted=False), many=True, context=self.context)
        return [image for image in serializer.data if image is not None]

    def get_attachments(self, obj):
        from adventures.serializers import AttachmentSerializer
        serializer = AttachmentSerializer(obj.attachments.filter(is_deleted=False), many=True, context=self.context)
        return [attachment for attachment in serializer.data if attachment is not None]


class RatingCountMixin:
    """
    Mixin providing get_rating_count() for entity serializers.

    Returns the count of visits that have a rating set.

    Used by: LocationSerializer, TransportationSerializer, LodgingSerializer
    """

    def get_rating_count(self, obj):
        """Return the count of visits with a rating."""
        return obj.visits.filter(rating__isnull=False).count()
