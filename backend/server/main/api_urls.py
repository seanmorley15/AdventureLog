"""Everything under ``/api/``: the API itself, its documentation, and allauth's headless sign-in."""

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from cloud.views import AccountViewSet
from core.routers import SingletonRouter
from .views import ServerInfoView

account_router = SingletonRouter()
account_router.register(r'account', AccountViewSet, basename='account')

urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api-schema'), name='api-docs'),
    path('docs/redoc/', SpectacularRedocView.as_view(url_name='api-schema'), name='api-redoc'),

    # django-allauth headless: /api/auth/browser/v1/... and /api/auth/app/v1/...
    path('auth/', include('allauth.headless.urls')),

    path('', include(account_router.urls)),
    path('', include('users.urls')),
    path('server-info/', ServerInfoView.as_view(), name='server-info'),
    path('integrations/', include('integrations.urls')),
    path('billing/', include('billing.urls')),
    # adventures first: it routes visited-regions/sync/, which the visited-regions router would take.
    path('', include('adventures.urls')),
    path('', include('worldtravel.urls')),
]
