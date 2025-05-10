from django.contrib.auth.backends import ModelBackend
from allauth.socialaccount.models import SocialAccount

class NoPasswordAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # First, attempt normal authentication
        user = super().authenticate(request, username=username, password=password, **kwargs)
        if user is None:
            return None
        
        if SocialAccount.objects.filter(user=user).exists() and user.disable_password:
            # If yes, disable login via password
            return None
        
        return user
