"""Integration routes. Mounted at ``api/integrations/``. Each integration is a per-user singleton."""

from django.urls import include, path

from core.routers import SingletonRouter
from integrations.views import EndurainViewSet, ImmichViewSet, IntegrationStatusView, StravaViewSet, WandererViewSet

router = SingletonRouter()
router.register(r'immich', ImmichViewSet, basename='immich')
router.register(r'strava', StravaViewSet, basename='strava')
router.register(r'wanderer', WandererViewSet, basename='wanderer')
router.register(r'endurain', EndurainViewSet, basename='endurain')

urlpatterns = [
    path('', IntegrationStatusView.as_view(), name='integrations'),
    path('', include(router.urls)),
]
