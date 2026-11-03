from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView, TemplateView

from users.invitations.views import AcceptInviteView
from .views import FrontendSignupRedirectView, health_check, serve_protected_media

urlpatterns = [
    # The API, its docs, and headless sign-in. See API.md.
    path('api/', include('main.api_urls')),

    # Protected media files
    re_path(r'^media/(?P<path>.*)$', serve_protected_media, name='serve-protected-media'),

    path('health/', health_check, name='health_check'),

    # The link in invitation emails. The library's own route also matches without the
    # trailing slash, so register ours for both before including it.
    re_path(r'^invitations/accept-invite/(?P<key>\w+)/?$', AcceptInviteView.as_view(), name='accept-invite'),
    path('invitations/', include('invitations.urls', namespace='invitations')),

    path('', TemplateView.as_view(template_name='home.html')),

    re_path(r'^admin/', admin.site.urls),
    re_path(r'^accounts/profile/$', RedirectView.as_view(url='/', permanent=True), name='profile-redirect'),
    # Signup happens in the SvelteKit frontend via the headless API.
    path('accounts/signup/', FrontendSignupRedirectView.as_view(), name='server_signup_redirect'),
    # Server-rendered allauth: social sign-in and the OAuth callbacks registered with providers.
    path('accounts/', include('allauth.urls')),
]
