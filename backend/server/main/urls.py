from django.urls import include, re_path, path
from django.contrib import admin
from django.views.generic import RedirectView, TemplateView
from users.views import IsRegistrationDisabled, PublicUserListView, PublicUserDetailView, UserMetadataView, UpdateUserMetadataView, EnabledSocialProvidersView, DisablePasswordAuthenticationView
from .views import get_csrf_token, get_public_url, serve_protected_media
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
    path("auth/", include("allauth.headless.urls")),

    # Serve protected media files
    re_path(r'^media/(?P<path>.*)$', serve_protected_media, name='serve-protected-media'),

    path('auth/is-registration-disabled/', IsRegistrationDisabled.as_view(), name='is_registration_disabled'),
    path('auth/users/', PublicUserListView.as_view(), name='public-user-list'),
    path('auth/user/<str:username>/', PublicUserDetailView.as_view(), name='public-user-detail'),
    path('auth/update-user/', UpdateUserMetadataView.as_view(), name='update-user-metadata'),

    path('auth/user-metadata/', UserMetadataView.as_view(), name='user-metadata'),

    path('auth/social-providers/', EnabledSocialProvidersView.as_view(), name='enabled-social-providers'),

    path('auth/disable-password/', DisablePasswordAuthenticationView.as_view(), name='disable-password-authentication'),

    path('csrf/', get_csrf_token, name='get_csrf_token'),
    path('public-url/', get_public_url, name='get_public_url'),
    
    path('', TemplateView.as_view(template_name='home.html')),
    
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^accounts/profile/$', RedirectView.as_view(url='/',
            permanent=True), name='profile-redirect'),
    re_path(r'^docs/$', schema_view.with_ui('swagger',
            cache_timeout=0), name='api_docs'),
    # path('auth/account-confirm-email/', VerifyEmailView.as_view(), name='account_email_verification_sent'),
    path("accounts/", include("allauth.urls")),

    path("api/integrations/", include("integrations.urls")),

    # Include the API endpoints:   
]