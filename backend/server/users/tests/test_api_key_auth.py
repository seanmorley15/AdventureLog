from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone
from rest_framework.test import APITestCase

from users.models import APIKey, CustomUser


class APIKeyAuthenticationTests(APITestCase):
    URL = '/api/account/'

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='key-user', email='key-user@example.com', password='testpassword123'
        )
        _, self.raw_key = APIKey.generate(user=self.user, name='Test key')

    def test_valid_key_authenticates_with_either_header(self):
        by_header = self.client.get(self.URL, HTTP_X_API_KEY=self.raw_key)
        by_authorization = self.client.get(self.URL, HTTP_AUTHORIZATION=f'Api-Key {self.raw_key}')

        self.assertEqual(by_header.status_code, 200)
        self.assertEqual(by_authorization.status_code, 200)
        self.assertEqual(by_header.json()['user']['username'], 'key-user')

    def test_unknown_key_is_rejected(self):
        response = self.client.get(self.URL, HTTP_X_API_KEY='al_not-a-real-key')

        self.assertEqual(response.status_code, 401)

    def test_key_stops_working_when_the_user_is_deactivated(self):
        self.user.is_active = False
        self.user.save()

        response = self.client.get(self.URL, HTTP_X_API_KEY=self.raw_key)

        self.assertEqual(response.status_code, 401)

    def test_key_works_again_when_the_user_is_reactivated(self):
        self.user.is_active = False
        self.user.save()
        self.user.is_active = True
        self.user.save()

        response = self.client.get(self.URL, HTTP_X_API_KEY=self.raw_key)

        self.assertEqual(response.status_code, 200)

    def test_key_hash_is_not_stored_in_plaintext(self):
        stored = APIKey.objects.get(user=self.user)

        self.assertNotIn(self.raw_key, (stored.key_hash, stored.key_prefix))
        self.assertTrue(self.raw_key.startswith(stored.key_prefix))


class APIKeyHashingTests(APITestCase):
    URL = '/api/account/'

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='hash-user', email='hash-user@example.com', password='testpassword123'
        )

    def _legacy_key(self, raw_key='al_legacy-token-value-0123456789abcdef0123456789'):
        """A key stored the way keys were before the fast hash: PBKDF2 in key_hash only."""
        row = APIKey.objects.create(
            user=self.user, name='Old key', key_prefix=raw_key[:12], key_hash=APIKey._legacy_hash(raw_key)
        )
        return row, raw_key

    def test_new_keys_are_stored_under_the_fast_hash_only(self):
        row, raw_key = APIKey.generate(user=self.user, name='New key')

        self.assertIsNone(row.key_hash)
        self.assertEqual(row.key_hash_v2, APIKey._fast_hash(raw_key))
        self.assertEqual(len(row.key_hash_v2), 64)

    def test_authenticating_a_new_key_does_no_slow_hashing(self):
        _, raw_key = APIKey.generate(user=self.user, name='New key')

        with patch('users.models.hashlib.pbkdf2_hmac') as slow_hash:
            self.assertEqual(self.client.get(self.URL, HTTP_X_API_KEY=raw_key).status_code, 200)

        slow_hash.assert_not_called()

    def test_made_up_keys_never_trigger_the_slow_hash(self):
        APIKey.generate(user=self.user, name='New key')
        self._legacy_key()

        with patch('users.models.hashlib.pbkdf2_hmac') as slow_hash:
            for guess in ('al_nothing', 'al_zzzzzzzzzzzzzzzzzzzzzzzz', 'x' * 60):
                self.assertEqual(self.client.get(self.URL, HTTP_X_API_KEY=guess).status_code, 401)

        slow_hash.assert_not_called()

    def test_a_legacy_key_still_works_and_is_moved_to_the_fast_hash(self):
        row, raw_key = self._legacy_key()

        first = self.client.get(self.URL, HTTP_X_API_KEY=raw_key)

        self.assertEqual(first.status_code, 200)
        row.refresh_from_db()
        self.assertIsNone(row.key_hash)
        self.assertEqual(row.key_hash_v2, APIKey._fast_hash(raw_key))

        with patch('users.models.hashlib.pbkdf2_hmac') as slow_hash:
            self.assertEqual(self.client.get(self.URL, HTTP_X_API_KEY=raw_key).status_code, 200)
        slow_hash.assert_not_called()

    def test_a_wrong_key_with_a_legacy_keys_prefix_is_refused_and_leaves_it_alone(self):
        row, raw_key = self._legacy_key()
        forged = raw_key[:12] + 'forged-rest-of-the-token'

        response = self.client.get(self.URL, HTTP_X_API_KEY=forged)

        self.assertEqual(response.status_code, 401)
        row.refresh_from_db()
        self.assertIsNotNone(row.key_hash)
        self.assertIsNone(row.key_hash_v2)

    def test_last_used_is_recorded_but_not_rewritten_on_every_request(self):
        row, raw_key = APIKey.generate(user=self.user, name='New key')
        self.assertIsNone(row.last_used_at)

        self.client.get(self.URL, HTTP_X_API_KEY=raw_key)
        row.refresh_from_db()
        first_seen = row.last_used_at
        self.assertIsNotNone(first_seen)

        self.client.get(self.URL, HTTP_X_API_KEY=raw_key)
        row.refresh_from_db()
        self.assertEqual(row.last_used_at, first_seen)

        APIKey.objects.filter(pk=row.pk).update(last_used_at=timezone.now() - timedelta(minutes=10))
        self.client.get(self.URL, HTTP_X_API_KEY=raw_key)
        row.refresh_from_db()
        self.assertGreater(row.last_used_at, timezone.now() - timedelta(minutes=1))

    def test_keys_do_not_depend_on_the_secret_key(self):
        _, raw_key = APIKey.generate(user=self.user, name='New key')

        with self.settings(SECRET_KEY='a-completely-different-secret-key-value'):
            self.assertEqual(self.client.get(self.URL, HTTP_X_API_KEY=raw_key).status_code, 200)
