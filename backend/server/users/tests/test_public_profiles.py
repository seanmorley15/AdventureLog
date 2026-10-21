from rest_framework.test import APITestCase

from adventures.models import Collection
from users.models import CustomUser

PRIVATE_FIELDS = ('has_password', 'disable_password', 'shared_collection_count', 'pending_collection_invite_count')


class PublicProfileFieldTests(APITestCase):
    def setUp(self):
        self.viewer = CustomUser.objects.create_user(
            username='profile-viewer', email='profile-viewer@example.com', password='testpassword123'
        )
        self.person = CustomUser.objects.create_user(
            username='profile-person', email='profile-person@example.com', password='testpassword123',
            public_profile=True,
        )
        Collection.objects.create(user=self.viewer, name='Theirs').shared_with.add(self.person)

    def test_detail_view_hides_account_fields_of_other_users(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(f'/api/users/{self.person.username}/')

        self.assertEqual(response.status_code, 200)
        user = response.json()['user']
        self.assertEqual(user['username'], 'profile-person')
        for field in PRIVATE_FIELDS:
            self.assertNotIn(field, user)

    def test_detail_view_works_for_anonymous_visitors_and_hides_account_fields(self):
        response = self.client.get(f'/api/users/{self.person.username}/')

        self.assertEqual(response.status_code, 200)
        for field in PRIVATE_FIELDS:
            self.assertNotIn(field, response.json()['user'])

    def test_list_view_hides_account_fields(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get('/api/users/')

        self.assertEqual(response.status_code, 200)
        people = response.json()
        self.assertEqual([p['username'] for p in people], ['profile-person'])
        for field in PRIVATE_FIELDS:
            self.assertNotIn(field, people[0])

    def test_own_metadata_still_includes_account_fields(self):
        self.client.force_authenticate(user=self.person)

        response = self.client.get('/api/account/')

        self.assertEqual(response.status_code, 200)
        for field in PRIVATE_FIELDS:
            self.assertIn(field, response.json()['user'])
