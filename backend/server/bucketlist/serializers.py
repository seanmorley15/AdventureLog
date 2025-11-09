from rest_framework import serializers
from main.utils import CustomModelSerializer
from .models import BucketItem
from adventures.serializers import ContentImageSerializer, AttachmentSerializer


class BucketItemSerializer(CustomModelSerializer):
    images = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    location_name = serializers.SerializerMethodField()
    
    class Meta:
        model = BucketItem
        fields = (
            'id', 'user', 'title', 'description', 'tags', 'status', 'location', 'location_name', 'notes', 
            'is_public', 'created_at', 'updated_at', 'images', 'attachments'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at', 'location_name')
    
    def get_images(self, obj):
        serializer = ContentImageSerializer(obj.images.all(), many=True, context=self.context)
        return serializer.data
    
    def get_attachments(self, obj):
        serializer = AttachmentSerializer(obj.attachments.all(), many=True, context=self.context)
        return serializer.data
    
    def get_location_name(self, obj):
        if obj.location:
            return obj.location.name
        return None
