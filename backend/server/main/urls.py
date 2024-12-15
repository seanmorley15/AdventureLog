from django.urls import include, re_path, path
from django.contrib import admin
from django.views.generic import RedirectView, TemplateView
from django.conf import settings
from django.conf.urls.static import static
from users.views import IsRegistrationDisabled, PublicUserListView, PublicUserDetailView, UserMetadataView, UpdateUserMetadataView
from .views import get_csrf_token
from drf_yasg.views import get_schema_view

from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title='API Docs',
        default_version='v1',
    )
)
urlpatterns = [
    path('api/', include('adventures.urls')),
    path('api/', include('worldtravel.urls')),
    path("_allauth/", include("allauth.headless.urls")),

    path('auth/is-registration-disabled/', IsRegistrationDisabled.as_view(), name='is_registration_disabled'),
    path('auth/users/', PublicUserListView.as_view(), name='public-user-list'),
    path('auth/user/<uuid:user_id>/', PublicUserDetailView.as_view(), name='public-user-detail'),
    path('auth/update-user/', UpdateUserMetadataView.as_view(), name='update-user-metadata'),

    path('auth/user-metadata/', UserMetadataView.as_view(), name='user-metadata'),

    path('csrf/', get_csrf_token, name='get_csrf_token'),
    
    path('', TemplateView.as_view(template_name='home.html')),
    
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^accounts/profile/$', RedirectView.as_view(url='/',
            permanent=True), name='profile-redirect'),
    re_path(r'^docs/$', schema_view.with_ui('swagger',
            cache_timeout=0), name='api_docs'),
    # path('auth/account-confirm-email/', VerifyEmailView.as_view(), name='account_email_verification_sent'),
    path("accounts/", include("allauth.urls")),

    # Include the API endpoints:
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
