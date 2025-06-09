from django.contrib.auth.backends import ModelBackend
from allauth.socialaccount.models import SocialAccount
from allauth.account.auth_backends import AuthenticationBackend as AllauthBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class NoPasswordAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
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
        
        try:
            # Get the user first
            user = User.objects.get(username=username)
        except User.DoesNotExist:
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