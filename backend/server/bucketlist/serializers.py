
from rest_framework import serializers
from main.utils import CustomModelSerializer
from .models import BucketItem
from adventures.serializers import ContentImageSerializer, AttachmentSerializer, LocationSerializer
from adventures.models import Location


class BucketItemSerializer(CustomModelSerializer):
    # Images and attachments
    images = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    
    # Location - nested read representation
    location = LocationSerializer(read_only=True)
    # Accept a location id on create/update (write-only)
    location_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source='location',
        queryset=Location.objects.all(),
        allow_null=True,
        required=False
    )
    
    class Meta:
        model = BucketItem
        fields = (
            'id',
            'user',
            'title',
            'description',
            'tags',
            'status',
            'location',     # nested read representation
            'location_id',  # write-only id for create/update
            'notes',
            'is_public',
            'created_at',
            'updated_at',
            'images',
            'attachments'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')
    
    def get_images(self, obj):
        serializer = ContentImageSerializer(obj.images.all(), many=True, context=self.context)
        return serializer.data
    
    def get_attachments(self, obj):
        serializer = AttachmentSerializer(obj.attachments.all(), many=True, context=self.context)
        return serializer.data
