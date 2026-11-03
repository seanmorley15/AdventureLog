"""
Native clients sign in through allauth's headless *app* client and then send the session token
it returns as ``X-Session-Token``. These tests cover the token being accepted by the rest of
the API (DRF), by protected media, and by the hosted-plan check.
"""

from datetime import timedelta
from unittest import mock

from django.contrib.sessions.models import Session
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from billing.models import Subscription
from users.middleware import DisableCSRFForHeaderCredentialsMiddleware
from users.models import APIKey, CustomUser

APP_LOGIN = '/api/auth/app/v1/auth/login'
APP_SESSION = '/api/auth/app/v1/auth/session'
PASSWORD = 'testpassword123'


def app_login(client, username='tok-user', password=PASSWORD):
    """Sign in like the mobile app does and return the session token."""
    response = client.post(APP_LOGIN, {'username': username, 'password': password}, format='json')
    assert response.status_code == 200, response.content
    return response.json()['meta']['session_token']


class SessionTokenAuthenticationTests(APITestCase):
    URL = '/api/account/'

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='tok-user', email='tok-user@example.com', password=PASSWORD
        )
        self.token = app_login(self.client)
        # The app sends only the header: no cookies from the login response.
        self.client.cookies.clear()

    def test_token_from_app_login_authenticates_the_api(self):
        response = self.client.get(self.URL, HTTP_X_SESSION_TOKEN=self.token)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user']['username'], 'tok-user')

    def test_unknown_token_is_unauthorized(self):
        response = self.client.get(self.URL, HTTP_X_SESSION_TOKEN='not-a-real-session')

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['code'], 'authentication_failed')

    def test_no_credentials_is_still_unauthorized(self):
        self.assertEqual(self.client.get(self.URL).status_code, 401)

    def test_the_app_client_recognises_its_own_token(self):
        """allauth's own session route must see the user too (the app uses it to check sign-in)."""
        response = self.client.get(APP_SESSION, HTTP_X_SESSION_TOKEN=self.token)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['meta']['is_authenticated'])

    def test_logging_out_revokes_the_token(self):
        logout = self.client.delete(APP_SESSION, HTTP_X_SESSION_TOKEN=self.token)
        self.assertEqual(logout.status_code, 401)  # allauth answers "no longer authenticated"

        self.assertFalse(Session.objects.filter(session_key=self.token).exists())
        response = self.client.get(self.URL, HTTP_X_SESSION_TOKEN=self.token)
        self.assertEqual(response.status_code, 401)

    def test_deactivated_user_is_rejected(self):
        self.user.is_active = False
        self.user.save()

        response = self.client.get(self.URL, HTTP_X_SESSION_TOKEN=self.token)

        self.assertEqual(response.status_code, 401)

    def test_changing_the_password_revokes_the_token(self):
        self.user.set_password('a-different-password-456')
        self.user.save()

        response = self.client.get(self.URL, HTTP_X_SESSION_TOKEN=self.token)

        self.assertEqual(response.status_code, 401)

    def test_a_session_that_is_not_signed_in_is_rejected(self):
        """A pending step (such as the second factor) holds a session with no user in it."""
        from allauth.headless.internal.sessionkit import new_session

        session = new_session()
        session['pending'] = 'mfa'
        session.save()

        response = self.client.get(self.URL, HTTP_X_SESSION_TOKEN=session.session_key)

        self.assertEqual(response.status_code, 401)

    def test_unsafe_methods_need_no_csrf_token(self):
        client = APIClient(enforce_csrf_checks=True)
        key, _ = APIKey.generate(user=self.user, name='to delete')
        response = client.delete(
            f'/api/account/api-keys/{key.id}/', HTTP_X_SESSION_TOKEN=self.token
        )

        self.assertEqual(response.status_code, 204)

    def test_using_the_token_extends_an_old_session(self):
        key = self.token
        Session.objects.filter(session_key=key).update(expire_date=timezone.now() + timedelta(hours=1))
        from allauth.headless.internal.sessionkit import session_store

        stale = session_store(key)
        stale['_session_touch'] = 1  # long ago
        stale.save()
        Session.objects.filter(session_key=key).update(expire_date=timezone.now() + timedelta(hours=1))

        self.client.get(self.URL, HTTP_X_SESSION_TOKEN=key)

        expires = Session.objects.get(session_key=key).expire_date
        self.assertGreater(expires, timezone.now() + timedelta(days=1))

    def test_the_token_is_not_logged_or_returned(self):
        response = self.client.get(self.URL, HTTP_X_SESSION_TOKEN=self.token)

        self.assertNotIn(self.token, response.content.decode())


class SessionTokenProtectedMediaTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='media-user', email='media-user@example.com', password=PASSWORD
        )
        self.token = app_login(APIClient(), username='media-user')

    def _get(self, **headers):
        with mock.patch('main.views.check_file_permission', return_value=True) as check, \
                mock.patch('main.views._serve_media_file', return_value=HttpResponse('file')):
            response = self.client.get('/media/images/photo.webp', **headers)
        return response, check

    def test_token_identifies_the_user_to_the_permission_check(self):
        response, check = self._get(HTTP_X_SESSION_TOKEN=self.token)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(check.call_args.args[1], self.user)

    def test_a_bad_token_is_treated_as_anonymous(self):
        response, check = self._get(HTTP_X_SESSION_TOKEN='nope')

        self.assertIsNone(check.call_args.args[1])
        self.assertEqual(response.status_code, 200)  # the mocked check allowed it; the user was None


@override_settings(CLOUD_MODE=True)
class SessionTokenCloudAccessTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='tok-user', email='tok-user@example.com', password=PASSWORD
        )
        self.subscription = Subscription.objects.get(user=self.user)
        self.token = app_login(self.client)
        self.client.cookies.clear()

    def _set_status(self, status):
        self.subscription.status = status
        self.subscription.trial_ends_at = None
        self.subscription.save()

    def test_a_token_without_a_plan_gets_402(self):
        self._set_status(Subscription.STATUS_CANCELED)

        response = self.client.get('/api/lodgings/', HTTP_X_SESSION_TOKEN=self.token)

        self.assertEqual(response.status_code, 402)
        self.assertEqual(response.json()['code'], 'subscription_required')

    def test_a_token_with_a_plan_is_allowed(self):
        self._set_status(Subscription.STATUS_ACTIVE)

        response = self.client.get('/api/lodgings/', HTTP_X_SESSION_TOKEN=self.token)

        self.assertEqual(response.status_code, 200)


class HeaderCredentialsCsrfMiddlewareTests(TestCase):
    """The safety net for non-DRF views: header credentials are not cookie-borne, so no CSRF."""

    def _exempt(self, **extra):
        request = RequestFactory().post('/x/', **extra)
        DisableCSRFForHeaderCredentialsMiddleware(lambda r: None).process_request(request)
        return getattr(request, '_dont_enforce_csrf_checks', False)

    def test_session_token_header_is_exempt(self):
        self.assertTrue(self._exempt(HTTP_X_SESSION_TOKEN='abc'))

    def test_api_key_is_still_exempt(self):
        self.assertTrue(self._exempt(HTTP_X_API_KEY='al_abc'))

    def test_a_session_cookie_always_keeps_csrf_on(self):
        request = RequestFactory().post('/x/', HTTP_X_SESSION_TOKEN='abc')
        request.COOKIES['sessionid'] = 'cookie'
        DisableCSRFForHeaderCredentialsMiddleware(lambda r: None).process_request(request)

        self.assertFalse(getattr(request, '_dont_enforce_csrf_checks', False))

    def test_no_header_keeps_csrf_on(self):
        self.assertFalse(self._exempt())
