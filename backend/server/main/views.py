from django.http import JsonResponse
from django.middleware.csrf import get_token
from os import getenv
from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views.static import serve
from adventures.utils.file_permissions import checkFilePermission

def get_csrf_token(request):
    csrf_token = get_token(request)
    return JsonResponse({'csrfToken': csrf_token})

def get_public_url(request):
    return JsonResponse({'PUBLIC_URL': getenv('PUBLIC_URL')})

protected_paths = ['images/', 'attachments/']

def serve_protected_media(request, path):
    if any([path.startswith(protected_path) for protected_path in protected_paths]):
        image_id = path.split('/')[1]
        user = request.user
        media_type =  path.split('/')[0] + '/'
        if checkFilePermission(image_id, user, media_type):
            if settings.DEBUG:
                # In debug mode, serve the file directly
                return serve(request, path, document_root=settings.MEDIA_ROOT)
            else:
                # In production, use X-Accel-Redirect to serve the file using Nginx
                response = HttpResponse()
                response['Content-Type'] = ''
                response['X-Accel-Redirect'] = '/protectedMedia/' + path
                return response
        else:
            return HttpResponseForbidden()
    else:
        if settings.DEBUG:
            return serve(request, path, document_root=settings.MEDIA_ROOT)
        else:
            response = HttpResponse()
            response['Content-Type'] = ''
            response['X-Accel-Redirect'] = '/protectedMedia/' + path
            return response