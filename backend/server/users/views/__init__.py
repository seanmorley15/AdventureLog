"""The users app's API views, grouped by what they are for."""

from .account import (
    DeleteAccountView,
    DisablePasswordAuthenticationView,
    UpdateUserMetadataView,
    UserMediaUsageView,
    UserMetadataView,
)
from .api_keys import APIKeyDetailView, APIKeyListCreateView
from .auth_config import (
    EnabledSocialProvidersView,
    IsRegistrationDisabled,
    PasswordPolicyView,
    SignupLegalLinksView,
)
from .mobile import MobileQRCodeView
from .public import PublicUserDetailView, PublicUserListView

__all__ = [
    'APIKeyDetailView', 'APIKeyListCreateView', 'DeleteAccountView', 'DisablePasswordAuthenticationView',
    'EnabledSocialProvidersView', 'IsRegistrationDisabled', 'MobileQRCodeView', 'PasswordPolicyView',
    'PublicUserDetailView', 'PublicUserListView', 'SignupLegalLinksView', 'UpdateUserMetadataView',
    'UserMediaUsageView', 'UserMetadataView',
]
