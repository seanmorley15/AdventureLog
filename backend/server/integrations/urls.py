from django.urls import path, include
from rest_framework.routers import DefaultRouter
from integrations.views import ImmichIntegrationView, IntegrationView

# Create the router and register the ViewSet
router = DefaultRouter()
router.register(r'immich', ImmichIntegrationView, basename='immich')
router.register(r'', IntegrationView, basename='integrations')

# Include the router URLs
urlpatterns = [
    path("", include(router.urls)),  # Includes /immich/ routes
]
