from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from allauth.usersessions.models import UserSession

User = get_user_model()


@override_settings(
    ACCOUNT_EMAIL_VERIFICATION='none',
    SESSION_SAVE_EVERY_REQUEST=False,
    USERSESSIONS_TRACK_ACTIVITY=False,
    SESSION_TOUCH_INTERVAL_SECONDS=60 * 60 * 24,
)
class UserSessionsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='sessionuser',
            email='sessionuser@example.com',
            password='testpassword123',
        )
        self.client = Client()

    def test_login_creates_user_session_and_middleware_tracks_once(self):
        self.assertTrue(self.client.login(username='sessionuser', password='testpassword123'))
        # Force a request so EfficientSessionMiddleware runs.
        response = self.client.get('/auth/current-user/')
        self.assertEqual(response.status_code, 200)

        sessions = UserSession.objects.filter(user=self.user)
        self.assertEqual(sessions.count(), 1)
        self.assertTrue(self.client.session.get('_al_us'))
        self.assertIsInstance(self.client.session.get('_session_touch'), int)

    def test_headless_sessions_list_and_revoke_other(self):
        self.assertTrue(self.client.login(username='sessionuser', password='testpassword123'))
        self.client.get('/auth/current-user/')

        # Simulate a second device session for the same user.
        other = Client()
        self.assertTrue(other.login(username='sessionuser', password='testpassword123'))
        other.get('/auth/current-user/')
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 2)

        list_resp = self.client.get('/auth/browser/v1/auth/sessions')
        self.assertEqual(list_resp.status_code, 200)
        payload = list_resp.json()
        self.assertEqual(len(payload['data']), 2)

        other_ids = [s['id'] for s in payload['data'] if not s['is_current']]
        self.assertEqual(len(other_ids), 1)

        delete_resp = self.client.delete(
            '/auth/browser/v1/auth/sessions',
            data={'sessions': other_ids},
            content_type='application/json',
        )
        self.assertEqual(delete_resp.status_code, 200)
        remaining = delete_resp.json()['data']
        self.assertEqual(len(remaining), 1)
        self.assertTrue(remaining[0]['is_current'])
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 1)

        # Other client session should no longer authenticate.
        other_resp = other.get('/auth/current-user/')
        self.assertIn(other_resp.status_code, (401, 403))
