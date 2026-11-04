from unittest import mock

from django.core.cache import cache
from rest_framework.test import APITestCase

from users.models import APIKey, CustomUser


class APIKeyAuthenticationTestCase(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = CustomUser.objects.create_user(
            username='apikeyuser', email='apikeyuser@example.com', password='testpassword'
        )
        self.api_key, self.raw_key = APIKey.generate(self.user, 'test key')

    def test_repeated_requests_hash_key_once(self):
        with mock.patch.object(APIKey, '_hash_raw_key', wraps=APIKey._hash_raw_key) as hash_raw_key:
            for _ in range(3):
                response = self.client.get('/api/collections/', HTTP_X_API_KEY=self.raw_key)
                self.assertEqual(response.status_code, 200)
        self.assertEqual(hash_raw_key.call_count, 1)

    def test_revoked_key_is_rejected_immediately(self):
        response = self.client.get('/api/collections/', HTTP_X_API_KEY=self.raw_key)
        self.assertEqual(response.status_code, 200)
        self.api_key.delete()
        response = self.client.get('/api/collections/', HTTP_X_API_KEY=self.raw_key)
        self.assertEqual(response.status_code, 401)

    def test_invalid_key_is_rejected(self):
        response = self.client.get('/api/collections/', HTTP_X_API_KEY='al_not-a-real-key')
        self.assertEqual(response.status_code, 401)
