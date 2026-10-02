# your_app/adapters.py

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.signals import user_signed_up
from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import resolve, Resolver404
from django.utils.translation import gettext_lazy as _

from users.invitation_signup import invite_email_for_request, request_has_valid_invite

HEADLESS_AUTH_PREFIXES = ('/auth/browser/', '/auth/app/')


def _is_headless_auth_request(request) -> bool:
    return request.path_info.startswith(HEADLESS_AUTH_PREFIXES)


def _allow_invite_signup(request) -> bool:
    if request_has_valid_invite(request):
        return True

    try:
        match = resolve(request.path_info)
        return match.view_name == 'invitations:accept-invite'
    except Resolver404:
        return False


class CustomAccountAdapter(DefaultAccountAdapter):
    """Control regular signup based on DISABLE_REGISTRATION, but allow invites."""

    def is_open_for_signup(self, request):
        """
        Allow signup only via the headless API used by the frontend app.
        Server-rendered allauth pages and other legacy routes stay closed.
        """
        if not _is_headless_auth_request(request):
            return _allow_invite_signup(request)

        if settings.DISABLE_REGISTRATION is False:
            return True

        return _allow_invite_signup(request)

    def clean_email(self, email):
        email = super().clean_email(email)
        invited_email = invite_email_for_request(self.request)
        if invited_email and email.lower() != invited_email.lower():
            raise ValidationError(
                _('You must sign up with the email address that received the invitation.')
            )
        return email

    def get_user_signed_up_signal(self):
        """Return the allauth `user_signed_up` signal for compatibility with
        django-invitations which expects this method on the adapter.
        """
        return user_signed_up


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Control social signup based on SOCIALACCOUNT_ALLOW_SIGNUP setting"""

    def is_open_for_signup(self, request, sociallogin):
        """
        Determines if social signup is allowed.
        Check SOCIALACCOUNT_ALLOW_SIGNUP env variable.

        Returning False shows the same 'signup_closed.html' template
        as regular signup, but only blocks NEW social signups.
        Existing users can still log in.
        """
        # If social signup is disabled, only allow existing users
        if not settings.SOCIALACCOUNT_ALLOW_SIGNUP:
            return sociallogin.is_existing

        return True
