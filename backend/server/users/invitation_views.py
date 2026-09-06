from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from invitations.adapters import get_invitations_adapter
from invitations.app_settings import app_settings
from invitations.views import AcceptInvite as BaseAcceptInvite
from rest_framework.response import Response
from rest_framework.views import APIView

from users.invitation_signup import inspect_invite_key, invitation_is_expired, stash_invite_email


class AcceptInviteView(BaseAcceptInvite):
    """Redirect invited users to the frontend signup page with the invite key."""

    def get_signup_redirect(self):
        key = self.kwargs.get('key', '')
        base = settings.INVITATIONS_SIGNUP_REDIRECT_URL.rstrip('/')
        return f'{base}?invite_key={key}'

    def post(self, *args, **kwargs):
        self.object = invitation = self.get_object()

        if app_settings.GONE_ON_ACCEPT_ERROR and (
            not invitation
            or (invitation and (invitation.accepted or invitation_is_expired(invitation)))
        ):
            from django.http import HttpResponse

            return HttpResponse(status=410)

        if not invitation:
            get_invitations_adapter().add_message(
                self.request,
                messages.ERROR,
                'invitations/messages/invite_invalid.txt',
            )
            return redirect(app_settings.LOGIN_REDIRECT)

        if invitation.accepted:
            get_invitations_adapter().add_message(
                self.request,
                messages.ERROR,
                'invitations/messages/invite_already_accepted.txt',
                {'email': invitation.email},
            )
            return redirect(app_settings.LOGIN_REDIRECT)

        if invitation_is_expired(invitation):
            get_invitations_adapter().add_message(
                self.request,
                messages.ERROR,
                'invitations/messages/invite_expired.txt',
                {'email': invitation.email},
            )
            return redirect(self.get_signup_redirect())

        if not app_settings.ACCEPT_INVITE_AFTER_SIGNUP:
            from invitations.views import accept_invitation

            accept_invitation(
                invitation=invitation,
                request=self.request,
                signal_sender=self.__class__,
            )

        get_invitations_adapter().stash_verified_email(self.request, invitation.email)
        return redirect(self.get_signup_redirect())


class InviteSignupStatusView(APIView):
    """Validate an invite key and stash the invited email in the Django session."""

    throttle_classes = []

    def get(self, request, key):
        status = inspect_invite_key(key)
        payload = {
            'valid': status.valid,
            'email': status.email,
            'expired': status.expired,
            'accepted': status.accepted,
            'registered': status.registered,
            'message': status.message,
        }

        if status.valid and status.email:
            stash_invite_email(request, status.email)
            request.session.modified = True

        return Response(payload, status=200 if status.valid else 400)
