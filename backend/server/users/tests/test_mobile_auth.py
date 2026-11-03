"""
Signing in to the mobile app through a provider the server already has (OIDC, GitHub...).

The app opens the system browser at ``/accounts/mobile/start/``. The browser signs in the usual
way, ``/accounts/mobile/complete/`` turns that into a one-time code sent back to the app, and the
app trades the code (with its PKCE verifier) at ``/api/auth/mobile/token/`` for an app session
token. Here the provider step is stood in for by ``force_login``.
"""

import base64
import hashlib
import secrets
from datetime import timedelta
from unittest import mock
from urllib.parse import parse_qs, urlencode, urlparse

from allauth.socialaccount.models import SocialApp
from allauth.usersessions.models import UserSession
from django.conf import settings
from django.contrib.sites.models import Site
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from users.models import CustomUser, MobileAuthCode

REDIRECT = 'adventurelog://auth/callback'
START = '/accounts/mobile/start/'
COMPLETE = '/accounts/mobile/complete/'
TOKEN = '/api/auth/mobile/token/'


def pkce_pair():
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode()).digest()
    return verifier, base64.urlsafe_b64encode(digest).rstrip(b'=').decode()


def query(response):
    return {k: v[0] for k, v in parse_qs(urlparse(response['Location']).query).items()}


class MobileAuthTestCase(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='sso-user', email='sso-user@example.com', password='testpassword123'
        )
        app = SocialApp.objects.create(
            provider='openid_connect', provider_id='idp', name='Test IdP',
            client_id='client', secret='secret', settings={'server_url': 'https://idp.example.com'},
        )
        app.sites.add(Site.objects.get(pk=settings.SITE_ID))
        self.verifier, self.challenge = pkce_pair()
        self.state = secrets.token_urlsafe(16)

    def start(self, client=None, **overrides):
        params = {
            'provider': 'oidc/idp', 'code_challenge': self.challenge, 'code_challenge_method': 'S256',
            'state': self.state, 'redirect_uri': REDIRECT,
        }
        params.update(overrides)
        return (client or self.client).get(START + '?' + urlencode(params))

    def handoff(self, client=None):
        """Run ``start`` and return the signed ``h`` that rides along in the provider's ``next``."""
        response = self.start(client)
        self.assertEqual(response.status_code, 302, response.content)
        next_url = parse_qs(urlparse(response['Location']).query)['next'][0]
        return parse_qs(urlparse(next_url).query)['h'][0]

    def finish(self, client, h):
        return client.get(COMPLETE + '?' + urlencode({'h': h}))

    def sign_in_and_get_code(self):
        h = self.handoff()
        self.client.force_login(self.user)  # what the provider round trip leaves behind
        response = self.finish(self.client, h)
        self.assertEqual(response.status_code, 302)
        return query(response)['code']

    def redeem(self, code, **overrides):
        body = {'code': code, 'code_verifier': self.verifier, 'redirect_uri': REDIRECT}
        body.update(overrides)
        return APIClient().post(TOKEN, body, format='json')


class StartTests(MobileAuthTestCase):
    def test_sends_the_browser_to_the_servers_own_provider_login_and_back_to_complete(self):
        response = self.start()

        self.assertEqual(response.status_code, 302)
        location = urlparse(response['Location'])
        self.assertEqual(location.path, '/accounts/oidc/idp/login/')  # relative: stays on the browser's host
        self.assertFalse(location.netloc)
        next_url = urlparse(parse_qs(location.query)['next'][0])
        self.assertEqual(next_url.path, COMPLETE)

    def test_the_pkce_challenge_and_state_ride_in_a_signed_value_not_the_session(self):
        # allauth signs an already-signed-in browser out before a provider login, which flushes
        # the session, so the handoff cannot live there.
        self.client.force_login(self.user)
        h = self.handoff()

        self.assertNotIn(self.challenge, h)  # encoded and signed, not plain text
        self.assertNotIn('mobile', dict(self.client.session))

    def test_an_unregistered_redirect_uri_is_refused_without_redirecting(self):
        for bad in ('https://evil.example/cb', 'adventurelog://evil/callback', 'adventurelog://auth/callback/x', ''):
            with self.subTest(redirect_uri=bad):
                response = self.start(redirect_uri=bad)
                self.assertEqual(response.status_code, 400)
                self.assertNotIn('Location', response)

    def test_an_unknown_provider_returns_an_error_to_the_app(self):
        response = self.start(provider='oidc/not-configured')

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(REDIRECT + '?'))
        self.assertEqual(query(response)['error'], 'invalid_request')
        self.assertEqual(query(response)['state'], self.state)

    def test_only_s256_is_accepted(self):
        response = self.start(code_challenge_method='plain')

        self.assertEqual(query(response)['error'], 'invalid_request')

    def test_a_malformed_challenge_is_refused(self):
        for bad in ('', 'short', 'x' * 44, '!' * 43):
            with self.subTest(challenge=bad):
                response = self.start(code_challenge=bad)
                self.assertEqual(query(response)['error'], 'invalid_request')

    def test_state_is_required(self):
        response = self.start(state='')

        self.assertEqual(query(response)['error'], 'invalid_request')


class CompleteTests(MobileAuthTestCase):
    def test_a_signed_in_browser_gets_a_one_time_code_sent_to_the_app(self):
        h = self.handoff()
        self.client.force_login(self.user)

        response = self.finish(self.client, h)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(REDIRECT + '?'))
        params = query(response)
        self.assertEqual(params['state'], self.state)
        self.assertNotIn('error', params)
        stored = MobileAuthCode.objects.get()
        self.assertEqual(stored.user, self.user)
        self.assertNotEqual(stored.code_hash, params['code'])  # only a hash is stored
        self.assertEqual(stored.code_hash, hashlib.sha256(params['code'].encode()).hexdigest())

    def test_a_browser_that_is_not_signed_in_gets_access_denied(self):
        h = self.handoff()

        response = self.finish(self.client, h)

        self.assertEqual(query(response)['error'], 'access_denied')
        self.assertEqual(query(response)['state'], self.state)
        self.assertFalse(MobileAuthCode.objects.exists())

    def test_a_tampered_value_is_refused_without_redirecting(self):
        h = self.handoff()
        self.client.force_login(self.user)

        response = self.finish(self.client, h[:-2] + ('AA' if h[-2:] != 'AA' else 'BB'))

        self.assertEqual(response.status_code, 400)
        self.assertNotIn('Location', response)

    def test_a_missing_value_is_refused(self):
        self.client.force_login(self.user)

        self.assertEqual(self.client.get(COMPLETE).status_code, 400)

    def test_an_old_handoff_is_refused(self):
        h = self.handoff()
        self.client.force_login(self.user)

        with mock.patch('django.core.signing.time.time', return_value=timezone.now().timestamp() + 3600):
            response = self.finish(self.client, h)

        self.assertEqual(response.status_code, 400)

    def test_the_browser_session_it_created_is_ended(self):
        h = self.handoff()  # anonymous when the handoff started
        self.client.force_login(self.user)
        self.finish(self.client, h)

        self.assertEqual(self.client.get('/api/account/').status_code, 401)

    def test_a_web_session_that_already_existed_is_left_alone(self):
        self.client.force_login(self.user)  # signed in to the website before the app asked
        h = self.handoff()

        self.finish(self.client, h)

        self.assertEqual(self.client.get('/api/account/').status_code, 200)

    def test_the_code_is_short_lived(self):
        code = self.sign_in_and_get_code()

        self.assertLessEqual(
            MobileAuthCode.objects.get().expires_at, timezone.now() + timedelta(seconds=60)
        )
        self.assertTrue(code)


class TokenTests(MobileAuthTestCase):
    def test_the_code_and_verifier_become_an_app_session(self):
        code = self.sign_in_and_get_code()

        response = self.redeem(code)

        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertTrue(body['meta']['is_authenticated'])
        token = body['meta']['session_token']
        me = APIClient().get('/api/account/', HTTP_X_SESSION_TOKEN=token)
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()['user']['username'], 'sso-user')

    def test_the_session_is_listed_so_it_can_be_revoked(self):
        token = self.redeem(self.sign_in_and_get_code()).json()['meta']['session_token']

        self.assertTrue(UserSession.objects.filter(user=self.user, session_key=token).exists())

    def test_a_wrong_verifier_is_refused_and_burns_the_code(self):
        code = self.sign_in_and_get_code()

        wrong = self.redeem(code, code_verifier=secrets.token_urlsafe(48))
        right = self.redeem(code)

        self.assertEqual(wrong.status_code, 400)
        self.assertEqual(wrong.json()['code'], 'invalid_grant')
        self.assertEqual(right.status_code, 400)

    def test_a_different_redirect_uri_is_refused(self):
        code = self.sign_in_and_get_code()

        response = self.redeem(code, redirect_uri='adventurelog://other/callback')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'invalid_grant')

    def test_a_code_works_once_and_a_replay_revokes_what_it_made(self):
        code = self.sign_in_and_get_code()
        token = self.redeem(code).json()['meta']['session_token']

        replay = self.redeem(code)

        self.assertEqual(replay.status_code, 400)
        self.assertEqual(replay.json()['code'], 'invalid_grant')
        revoked = APIClient().get('/api/account/', HTTP_X_SESSION_TOKEN=token)
        self.assertEqual(revoked.status_code, 401)

    def test_an_expired_code_is_refused(self):
        code = self.sign_in_and_get_code()
        MobileAuthCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))

        self.assertEqual(self.redeem(code).status_code, 400)

    def test_an_unknown_code_is_refused(self):
        response = self.redeem('not-a-code')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'invalid_grant')

    def test_a_user_deactivated_in_between_is_refused(self):
        code = self.sign_in_and_get_code()
        self.user.is_active = False
        self.user.save()

        self.assertEqual(self.redeem(code).status_code, 400)

    def test_missing_fields_are_validation_errors(self):
        response = APIClient().post(TOKEN, {}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'validation_error')
        self.assertEqual(set(response.json()['fields']), {'code', 'code_verifier', 'redirect_uri'})

    def test_needs_no_sign_in_and_no_csrf_token(self):
        code = self.sign_in_and_get_code()

        response = APIClient(enforce_csrf_checks=True).post(
            TOKEN, {'code': code, 'code_verifier': self.verifier, 'redirect_uri': REDIRECT}, format='json'
        )

        self.assertEqual(response.status_code, 200)

    @override_settings(MOBILE_AUTH_REDIRECT_URIS=['myapp://cb'])
    def test_the_allowed_redirect_uris_are_configurable(self):
        self.assertEqual(self.start(redirect_uri='myapp://cb').status_code, 302)
        self.assertEqual(self.start(redirect_uri=REDIRECT).status_code, 400)


class DiscoveryTests(MobileAuthTestCase):
    def test_the_server_says_the_app_can_sign_in_this_way(self):
        body = self.client.get('/api/server-info/').json()

        self.assertIn('mobile_auth_v1', body['capabilities'])
        self.assertIn('conditional_writes_v1', body['capabilities'])
        self.assertIn('client_ids_v1', body['capabilities'])
        self.assertIsInstance(body['version'], str)

    def test_each_provider_has_the_id_the_app_passes_to_start(self):
        providers = self.client.get('/api/auth/config/').json()['social_providers']

        self.assertEqual([p['id'] for p in providers], ['oidc/idp'])
