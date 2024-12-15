from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings

class NoNewUsersAccountAdapter(DefaultAccountAdapter):
    """
    Disable new user registration.
    """
    def is_open_for_signup(self, request):
        is_disabled = getattr(settings, 'DISABLE_REGISTRATION', False)
        return not is_disabled