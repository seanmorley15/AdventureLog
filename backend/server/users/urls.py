"""Sign-in configuration, the signed-in account, and public profiles. Mounted at ``api/``."""

from django.urls import path

from .invitations.views import InviteSignupStatusView
from .views import (
    APIKeyDetailView,
    APIKeyListCreateView,
    AuthConfigView,
    CsrfTokenView,
    MobileKeyView,
    PublicUserDetailView,
    PublicUserListView,
    PublicUserStatsView,
)

# The account itself (``/api/account/`` and its actions) is routed by main.api_urls, because the
# hosted (cloud) app extends it with subscription details.
urlpatterns = [
    # What the sign-in and sign-up screens need before anyone is signed in
    path('auth/config/', AuthConfigView.as_view(), name='auth-config'),
    path('auth/csrf/', CsrfTokenView.as_view(), name='auth-csrf'),
    path('auth/invitations/<str:key>/', InviteSignupStatusView.as_view(), name='auth-invitation'),

    # The signed-in user's keys
    path('account/api-keys/', APIKeyListCreateView.as_view(), name='api-key-list'),
    path('account/api-keys/<uuid:pk>/', APIKeyDetailView.as_view(), name='api-key-detail'),
    path('account/mobile-key/', MobileKeyView.as_view(), name='mobile-key'),

    # Public profiles
    path('users/', PublicUserListView.as_view(), name='public-user-list'),
    path('users/<str:username>/', PublicUserDetailView.as_view(), name='public-user-detail'),
    path('users/<str:username>/stats/', PublicUserStatsView.as_view(), name='public-user-stats'),
]
