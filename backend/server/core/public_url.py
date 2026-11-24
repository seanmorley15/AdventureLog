import os
from django.conf import settings
from django.core.files.storage import default_storage

def get_public_url():
    public_url = os.environ.get('PUBLIC_URL', 'http://127.0.0.1:8000').rstrip('/')
    return public_url.replace("'", "")

def build_media_url(path):
    if not path:
        return None
    if getattr(settings, 'USE_S3_MEDIA', False):
        return default_storage.url(path)
    return f"{get_public_url()}/media/{path}"
