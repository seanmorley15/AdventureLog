from django.urls import path, include
from rest_framework.routers import DefaultRouter
from integrations.views import ImmichIntegrationView

# Create the router and register the ViewSet
router = DefaultRouter()
router.register(r'immich', ImmichIntegrationView, basename='immich')

# Include the router URLs
urlpatterns = [
    path("", include(router.urls)),  # Includes /immich/ routes
]
