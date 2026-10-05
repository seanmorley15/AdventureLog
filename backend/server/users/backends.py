from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from allauth.socialaccount.models import SocialAccount
from allauth.account.auth_backends import AuthenticationBackend as AllauthBackend
from allauth.account.utils import filter_users_by_email, filter_users_by_username
from django.contrib.auth import get_user_model

User = get_user_model()

class NoPasswordAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Block all password-based logins when social-only mode is enforced
        if getattr(settings, "FORCE_SOCIALACCOUNT_LOGIN", False) and password:
            return None

        # Handle allauth-specific authentication (like email login)
        allauth_backend = AllauthBackend()
        allauth_user = allauth_backend.authenticate(request, username=username, password=password, **kwargs)
        
        # If allauth handled it, check our password disable logic
        if allauth_user:
            has_social_accounts = SocialAccount.objects.filter(user=allauth_user).exists()
            if has_social_accounts and getattr(allauth_user, 'disable_password', False):
                return None
            if self.user_can_authenticate(allauth_user):
                return allauth_user
            return None
        
        # Fallback to regular username/password authentication
        if username is None or password is None:
            return None
        
        user = self._get_user_by_username_or_email(username)
        if user is None:
            return None
        
        # Check if this user has social accounts and password is disabled
        has_social_accounts = SocialAccount.objects.filter(user=user).exists()
        
        # If user has social accounts and disable_password is True, deny password login
        if has_social_accounts and getattr(user, 'disable_password', False):
            return None
        
        # Otherwise, proceed with normal password authentication
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None

    @staticmethod
    def _get_user_by_username_or_email(identifier):
        try:
            return filter_users_by_username(identifier).get()
        except User.DoesNotExist:
            pass

        email_matches = list(filter_users_by_email(identifier, prefer_verified=True))
        if len(email_matches) == 1:
            return email_matches[0]

        return None