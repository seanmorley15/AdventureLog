from django.http import JsonResponse
from django.middleware.csrf import get_token
from os import getenv
from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.views.static import serve
from django.core.files.storage import default_storage
from adventures.utils.file_permissions import (
    checkFilePermission,
    is_public_media_path,
    is_protected_media_path,
    normalize_media_request_path,
)

def get_csrf_token(request):
    csrf_token = get_token(request)
    return JsonResponse({'csrfToken': csrf_token})

def get_public_url(request):
    return JsonResponse({'PUBLIC_URL': getenv('PUBLIC_URL')})

def health_check(request):
    from django.db import connection
    try:
        connection.ensure_connection()
        return JsonResponse({'ok': True, 'db': 'connected'})
    except Exception:
        return JsonResponse({'ok': False, 'db': 'disconnected'}, status=503)

def _redirect_storage(path):
    storage_url = default_storage.url(path)
    return HttpResponseRedirect(storage_url)

def _resolve_user(request):
    user = request.user

    if not user.is_authenticated:
        from users.authentication import APIKeyAuthentication
        from rest_framework.exceptions import AuthenticationFailed
        try:
            result = APIKeyAuthentication().authenticate(request)
            if result is not None:
                user, _ = result
        except AuthenticationFailed:
            return None

    return user


def _serve_media_file(request, path):
    if settings.USE_S3_MEDIA:
        return _redirect_storage(path)
    if settings.DEBUG:
        return serve(request, path, document_root=settings.MEDIA_ROOT)
    response = HttpResponse()
    response['Content-Type'] = ''
    response['X-Accel-Redirect'] = '/protectedMedia/' + path
    return response


def serve_protected_media(request, path):
    normalized_path = normalize_media_request_path(path)
    if normalized_path is None:
        return HttpResponseForbidden()

    if is_public_media_path(normalized_path):
        return _serve_media_file(request, normalized_path)

    if not is_protected_media_path(normalized_path):
        return HttpResponseForbidden()

    path_parts = normalized_path.split('/', 1)
    if len(path_parts) < 2 or not path_parts[1]:
        return HttpResponseForbidden()

    user = _resolve_user(request)
    if user is None:
        return HttpResponseForbidden()

    media_type = path_parts[0] + '/'
    file_id = path_parts[1]

    if checkFilePermission(file_id, user, media_type):
        return _serve_media_file(request, normalized_path)

    return HttpResponseForbidden()