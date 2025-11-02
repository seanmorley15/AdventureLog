
from rest_framework import serializers
from main.utils import CustomModelSerializer
from .models import BucketItem
# add these imports
from adventures.serializers import LocationSerializer  # filepath: backend/server/adventures/serializers.py
from adventures.models import Location  # filepath: backend/server/adventures/models.py


class BucketItemSerializer(CustomModelSerializer):
    # Return nested location details on GET
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
            'updated_at'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')
