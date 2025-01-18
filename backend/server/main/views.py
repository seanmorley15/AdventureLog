from django.http import JsonResponse
from django.middleware.csrf import get_token
from os import getenv
from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.views.static import serve
from adventures.utils.check_adventure_image_permisison import checkAdventureImagePermission

def get_csrf_token(request):
    csrf_token = get_token(request)
    return JsonResponse({'csrfToken': csrf_token})

def get_public_url(request):
    return JsonResponse({'PUBLIC_URL': getenv('PUBLIC_URL')})

def serve_protected_media(request, path):
    if path.startswith('images/'):
        image_id = path.split('/')[1]
        user = request.user
        if checkAdventureImagePermission(image_id, user):
            if settings.DEBUG:
                # In debug mode, serve the file directly
                return serve(request, path, document_root=settings.MEDIA_ROOT)
            else:
                # In production, use X-Accel-Redirect
                response = HttpResponse()
                response['Content-Type'] = ''
                response['X-Accel-Redirect'] = '/protectedMedia/' + path
                return response
        else:
            return HttpResponseForbidden()
    else:
        response = HttpResponse()
        response['Content-Type'] = ''
        response['X-Accel-Redirect'] = '/protectedMedia/' + path
        return response
    