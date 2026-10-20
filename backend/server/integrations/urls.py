from django.urls import path, include
from rest_framework.routers import DefaultRouter
from integrations.views import (
    EndurainIntegrationViewSet,
    ImmichIntegrationView,
    ImmichIntegrationViewSet,
    IntegrationView,
    StravaIntegrationView,
    WandererIntegrationViewSet,
)

router = DefaultRouter()
# Two viewsets share the 'immich' prefix. ImmichIntegrationView holds the actions
# (search, albums, the image proxy); ImmichIntegrationViewSet is the CRUD for the stored
# integration, whose detail route would also match 'search' and 'albums' as a pk. The
# actions must be registered first. test_urls.py pins this order.
router.register(r'immich', ImmichIntegrationView, basename='immich')
router.register(r'immich', ImmichIntegrationViewSet, basename='immich_viewset')
router.register(r'', IntegrationView, basename='integrations')
router.register(r'strava', StravaIntegrationView, basename='strava')
router.register(r'wanderer', WandererIntegrationViewSet, basename='wanderer')
router.register(r'endurain', EndurainIntegrationViewSet, basename='endurain')

urlpatterns = [
    path("", include(router.urls)),
]
