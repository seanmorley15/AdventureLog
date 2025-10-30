from rest_framework import serializers
from main.utils import CustomModelSerializer
from .models import BucketItem


class BucketItemSerializer(CustomModelSerializer):
    class Meta:
        model = BucketItem
        fields = (
            'id', 'user', 'title', 'description', 'tags', 'status', 'location', 'notes', 'is_public', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')
