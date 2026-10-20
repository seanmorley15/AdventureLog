from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

from django.core import signing
from django.test import override_settings
from rest_framework.test import APITestCase

from integrations.models import StravaToken
from integrations.views.strava import STRAVA_STATE_SALT
from users.models import CustomUser


@override_settings(
    STRAVA_CLIENT_ID='12345',
    STRAVA_CLIENT_SECRET='secret',
    PUBLIC_URL='http://testserver',
    FRONTEND_URL='http://frontend.test',
)
class StravaOAuthStateTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='strava-user', email='strava-user@example.com', password='testpassword123'
        )
        self.other = CustomUser.objects.create_user(
            username='strava-other', email='strava-other@example.com', password='testpassword123'
        )
        self.client.force_authenticate(user=self.user)

    def _state_from_authorize(self):
        response = self.client.get('/api/integrations/strava/authorize/')
        self.assertEqual(response.status_code, 200)
        query = parse_qs(urlparse(response.json()['auth_url']).query)
        return query['state'][0]

    def _token_response(self):
        response = MagicMock(status_code=200)
        response.json.return_value = {
            'access_token': 'a', 'refresh_token': 'r', 'expires_at': 9999999999,
            'athlete': {'id': 7}, 'scope': 'read',
        }
        return response

    def test_authorize_url_carries_a_state(self):
        self.assertTrue(self._state_from_authorize())

    @patch('integrations.views.strava.requests.post')
    def test_callback_with_the_state_from_authorize_connects_the_account(self, post):
        post.return_value = self._token_response()
        state = self._state_from_authorize()

        response = self.client.get('/api/integrations/strava/callback/', {'code': 'abc', 'state': state})

        self.assertEqual(response.status_code, 302, getattr(response, 'content', b''))
        self.assertTrue(StravaToken.objects.filter(user=self.user).exists())

    @patch('integrations.views.strava.requests.post')
    def test_callback_without_a_state_is_refused(self, post):
        response = self.client.get('/api/integrations/strava/callback/', {'code': 'abc'})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'strava.invalid_state')
        post.assert_not_called()
        self.assertFalse(StravaToken.objects.exists())

    @patch('integrations.views.strava.requests.post')
    def test_callback_with_a_state_made_for_another_user_is_refused(self, post):
        foreign = signing.dumps({'user': self.other.pk}, salt=STRAVA_STATE_SALT)

        response = self.client.get('/api/integrations/strava/callback/', {'code': 'abc', 'state': foreign})

        self.assertEqual(response.status_code, 400)
        post.assert_not_called()
        self.assertFalse(StravaToken.objects.exists())

    @patch('integrations.views.strava.requests.post')
    def test_callback_with_a_forged_state_is_refused(self, post):
        response = self.client.get('/api/integrations/strava/callback/', {'code': 'abc', 'state': 'not-signed'})

        self.assertEqual(response.status_code, 400)
        post.assert_not_called()

    @patch('integrations.views.strava.requests.post')
    def test_callback_with_an_expired_state_is_refused(self, post):
        state = self._state_from_authorize()

        with patch('integrations.views.strava.STRAVA_STATE_MAX_AGE', -1):
            response = self.client.get('/api/integrations/strava/callback/', {'code': 'abc', 'state': state})

        self.assertEqual(response.status_code, 400)
        post.assert_not_called()
