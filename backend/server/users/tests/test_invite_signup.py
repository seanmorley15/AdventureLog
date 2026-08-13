from django.conf import settings
from django.test import override_settings
from rest_framework.test import APITestCase

from users.models import CustomUser


class InviteSignupTestCase(APITestCase):
    @override_settings(
        DISABLE_REGISTRATION=True,
    )
    def test_accept_invite_redirects_to_frontend_with_invite_key(self):
        from invitations.utils import get_invitation_model

        Invitation = get_invitation_model()
        invitation = Invitation.create('invited@example.com')
        invitation.sent = invitation.created
        invitation.save()

        response = self.client.get(f'/invitations/accept-invite/{invitation.key}/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            f'{settings.FRONTEND_URL.rstrip("/")}/signup?invite_key={invitation.key}',
        )

    @override_settings(DISABLE_REGISTRATION=True)
    def test_invite_signup_status_stashes_session_email(self):
        from invitations.utils import get_invitation_model

        Invitation = get_invitation_model()
        invitation = Invitation.create('invited@example.com')
        invitation.sent = invitation.created
        invitation.save()

        response = self.client.get(f'/auth/invite-signup/{invitation.key}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['valid'])
        self.assertEqual(data['email'], 'invited@example.com')
        self.assertEqual(self.client.session.get('account_verified_email'), 'invited@example.com')

    @override_settings(DISABLE_REGISTRATION=True)
    def test_invite_signup_status_allows_unsent_invites(self):
        from invitations.utils import get_invitation_model

        Invitation = get_invitation_model()
        invitation = Invitation.create('unsent@example.com')
        self.assertIsNone(invitation.sent)

        response = self.client.get(f'/auth/invite-signup/{invitation.key}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['valid'])
        self.assertEqual(data['email'], 'unsent@example.com')

    @override_settings(
        DISABLE_REGISTRATION=True,
        ACCOUNT_EMAIL_VERIFICATION='none',
    )
    def test_headless_signup_allowed_with_invite_session_when_registration_disabled(self):
        from invitations.utils import get_invitation_model

        Invitation = get_invitation_model()
        invitation = Invitation.create('invited@example.com')
        invitation.sent = invitation.created
        invitation.save()

        session = self.client.session
        session['account_verified_email'] = invitation.email
        session.save()

        response = self.client.post('/auth/browser/v1/auth/signup', {
            'username': 'inviteduser',
            'email': invitation.email,
            'password': 'testpassword12',
            'first_name': 'Invited',
            'last_name': 'User',
            'invite_key': invitation.key,
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CustomUser.objects.filter(username='inviteduser').exists())
        invitation.refresh_from_db()
        self.assertTrue(invitation.accepted)

    @override_settings(
        DISABLE_REGISTRATION=True,
        ACCOUNT_EMAIL_VERIFICATION='none',
    )
    def test_headless_signup_allowed_with_invite_key_only(self):
        """Signup works when invite_key is in the POST body without a prior session stash."""
        from invitations.utils import get_invitation_model

        Invitation = get_invitation_model()
        invitation = Invitation.create('keyonly@example.com')
        invitation.sent = invitation.created
        invitation.save()

        response = self.client.post('/auth/browser/v1/auth/signup', {
            'username': 'keyonlyuser',
            'email': invitation.email,
            'password': 'testpassword12',
            'first_name': 'Key',
            'last_name': 'Only',
            'invite_key': invitation.key,
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CustomUser.objects.filter(username='keyonlyuser').exists())

    @override_settings(DISABLE_REGISTRATION=True)
    def test_headless_signup_rejects_mismatched_invite_email(self):
        from invitations.utils import get_invitation_model

        Invitation = get_invitation_model()
        invitation = Invitation.create('invited@example.com')
        invitation.sent = invitation.created
        invitation.save()

        session = self.client.session
        session['account_verified_email'] = invitation.email
        session.save()

        response = self.client.post('/auth/browser/v1/auth/signup', {
            'username': 'wrongemailuser',
            'email': 'someoneelse@example.com',
            'password': 'testpassword12',
            'first_name': 'Wrong',
            'last_name': 'Email',
            'invite_key': invitation.key,
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CustomUser.objects.filter(username='wrongemailuser').exists())
