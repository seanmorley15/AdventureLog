from django.urls import include, re_path, path
from django.contrib import admin
from django.views.generic import RedirectView, TemplateView
from users.invitations.views import AcceptInviteView
from cloud.views import CurrentUserView
from .views import get_csrf_token, public_url_view, health_check, serve_protected_media, FrontendSignupRedirectView
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

    path('auth/', include('users.urls')),
    # The signed-in user joined with their subscription: the app's "who am I" call.
    path('auth/current-user/', CurrentUserView.as_view(), name='current-user'),

    path('csrf/', get_csrf_token, name='get_csrf_token'),
    path('health/', health_check, name='health_check'),
    path('public-url/', public_url_view, name='get_public_url'),

    path("invitations/accept-invite/<str:key>/", AcceptInviteView.as_view(), name="accept-invite"),
    path("invitations/", include('invitations.urls', namespace='invitations')),
    
    path('', TemplateView.as_view(template_name='home.html')),
    
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^accounts/profile/$', RedirectView.as_view(url='/',
            permanent=True), name='profile-redirect'),
    re_path(r'^docs/$', schema_view.with_ui('swagger',
            cache_timeout=0), name='api_docs'),
    # Signup happens in the SvelteKit frontend via the headless API.
    path(
        'accounts/signup/',
        FrontendSignupRedirectView.as_view(),
        name='server_signup_redirect',
    ),
    path("accounts/", include("allauth.urls")),

    path("api/integrations/", include("integrations.urls")),
    path("api/billing/", include("billing.urls")),

    # Include the API endpoints:   
]