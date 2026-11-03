from django.test import override_settings
from rest_framework.test import APITestCase

from billing.models import Subscription
from users.models import CustomUser


@override_settings(CLOUD_MODE=True)
class CloudAccessMiddlewareTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='cloud-user',
            email='cloud-user@example.com',
            password='testpassword123',
        )
        self.subscription = Subscription.objects.get(user=self.user)
        self.client.force_login(self.user)

    def _set_status(self, status):
        self.subscription.status = status
        self.subscription.trial_ends_at = None
        self.subscription.save()

    def test_canceled_subscription_blocks_api(self):
        self._set_status(Subscription.STATUS_CANCELED)
        response = self.client.get('/api/lodgings/')
        self.assertEqual(response.status_code, 402)
        self.assertEqual(response.json()['code'], 'subscription_required')

    def test_the_account_stays_available_without_access(self):
        self._set_status(Subscription.STATUS_CANCELED)
        response = self.client.get('/api/account/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['subscription']['status'], Subscription.STATUS_CANCELED)
        self.assertFalse(response.json()['has_access'])

    def test_sign_in_and_docs_stay_available_without_access(self):
        self._set_status(Subscription.STATUS_CANCELED)
        for path in ('/api/auth/config/', '/api/auth/csrf/', '/api/server-info/', '/api/schema/'):
            with self.subTest(path=path):
                self.assertNotEqual(self.client.get(path).status_code, 402)
        self.assertEqual(self.client.get('/api/lodgings/').status_code, 402)

    def test_active_subscription_allows_api(self):
        self._set_status(Subscription.STATUS_ACTIVE)
        response = self.client.get('/api/lodgings/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_anonymous_api_request_is_not_blocked_by_billing(self):
        self.client.logout()
        response = self.client.get('/api/lodgings/')
        self.assertEqual(response.status_code, 401)

    def test_non_api_path_ignores_subscription(self):
        self._set_status(Subscription.STATUS_CANCELED)
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
