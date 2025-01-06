from django.http import JsonResponse
from django.middleware.csrf import get_token
from os import getenv

def get_csrf_token(request):
    csrf_token = get_token(request)
    return JsonResponse({'csrfToken': csrf_token})

def get_public_url(request):
    return JsonResponse({'PUBLIC_URL': getenv('PUBLIC_URL')})