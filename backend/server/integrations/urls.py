from integrations.views import *
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from integrations.views import IntegrationView, StravaIntegrationView

# Create the router and register the ViewSet
router = DefaultRouter()
router.register(r'immich', ImmichIntegrationView, basename='immich')
router.register(r'', IntegrationView, basename='integrations')
router.register(r'immich', ImmichIntegrationViewSet, basename='immich_viewset')
router.register(r'strava', StravaIntegrationView, basename='strava')

# Include the router URLs
urlpatterns = [
    path("", include(router.urls)),  # Includes /immich/ routes
]
