"""Account and sign-in routes. Mounted at ``auth/`` by the project URLs."""

from django.urls import path

from .invitations.views import InviteSignupStatusView
from .views import (
    APIKeyDetailView,
    APIKeyListCreateView,
    DeleteAccountView,
    DisablePasswordAuthenticationView,
    EnabledSocialProvidersView,
    IsRegistrationDisabled,
    MobileQRCodeView,
    PasswordPolicyView,
    PublicUserDetailView,
    PublicUserListView,
    SignupLegalLinksView,
    UpdateUserMetadataView,
    UserMediaUsageView,
    UserMetadataView,
)

urlpatterns = [
    # What the sign-in and sign-up screens need before anyone is signed in
    path('is-registration-disabled/', IsRegistrationDisabled.as_view(), name='is_registration_disabled'),
    path('password-policy/', PasswordPolicyView.as_view(), name='password_policy'),
    path('signup-legal-links/', SignupLegalLinksView.as_view(), name='signup_legal_links'),
    path('invite-signup/<str:key>/', InviteSignupStatusView.as_view(), name='invite_signup_status'),
    path('social-providers/', EnabledSocialProvidersView.as_view(), name='enabled-social-providers'),

    # Public profiles
    path('users/', PublicUserListView.as_view(), name='public-user-list'),
    path('user/<str:username>/', PublicUserDetailView.as_view(), name='public-user-detail'),

    # The signed-in user's account
    path('update-user/', UpdateUserMetadataView.as_view(), name='update-user-metadata'),
    path('user-metadata/', UserMetadataView.as_view(), name='user-metadata'),
    path('user-media-usage/', UserMediaUsageView.as_view(), name='user-media-usage'),
    path('disable-password/', DisablePasswordAuthenticationView.as_view(), name='disable-password-authentication'),
    path('delete-account/', DeleteAccountView.as_view(), name='delete-account'),

    # API key management
    path('api-keys/', APIKeyListCreateView.as_view(), name='api-key-list-create'),
    path('api-keys/<uuid:pk>/', APIKeyDetailView.as_view(), name='api-key-detail'),

    # Mobile QR code for app login
    path('mobile-qr/', MobileQRCodeView.as_view(), name='mobile-qr-code'),
]
