import os
from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import serializers

def get_user_uuid(user):
    return str(user.uuid)

def get_public_url():
    public_url = os.environ.get('PUBLIC_URL', 'http://127.0.0.1:8000').rstrip('/')
    return public_url.replace("'", "")

def build_media_url(path):
    if not path:
        return None
    if getattr(settings, 'USE_S3_MEDIA', False):
        return default_storage.url(path)
    return f"{get_public_url()}/media/{path}"

class CustomModelSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if hasattr(instance, 'user') and instance.user:
            representation['user'] = get_user_uuid(instance.user)
        return representation