"""A place shows who owns it, but only the owner sees their own account details."""

from rest_framework.test import APITestCase

from adventures.models import Location
from users.models import CustomUser

ACCOUNT_ONLY = ('has_password', 'disable_password', 'shared_collection_count', 'pending_collection_invite_count')
PUBLIC = ('uuid', 'username')


class LocationOwnerPrivacyTests(APITestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='priv-owner', email='priv-owner@example.com', password='testpassword123'
        )
        self.reader = CustomUser.objects.create_user(
            username='priv-reader', email='priv-reader@example.com', password='testpassword123'
        )
        self.place = Location.objects.create(user=self.owner, name='Public spot', is_public=True)

    def owner_of(self, response):
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()['user']

    def test_the_owner_sees_their_own_account_details(self):
        self.client.force_authenticate(user=self.owner)

        owner = self.owner_of(self.client.get(f'/api/locations/{self.place.id}/'))

        for field in ACCOUNT_ONLY + PUBLIC:
            self.assertIn(field, owner)

    def test_another_signed_in_user_sees_only_public_details_of_the_owner(self):
        self.client.force_authenticate(user=self.reader)

        owner = self.owner_of(self.client.get(f'/api/locations/{self.place.id}/'))

        self.assertEqual(owner['username'], 'priv-owner')
        for field in ACCOUNT_ONLY:
            self.assertNotIn(field, owner)

    def test_an_anonymous_reader_sees_only_public_details_of_the_owner(self):
        owner = self.owner_of(self.client.get(f'/api/locations/{self.place.id}/'))

        self.assertEqual(owner['username'], 'priv-owner')
        for field in ACCOUNT_ONLY:
            self.assertNotIn(field, owner)

    def test_the_list_hides_them_from_other_users_too(self):
        self.client.force_authenticate(user=self.reader)

        response = self.client.get('/api/locations/', {'search': 'Public spot'})

        self.assertEqual(response.status_code, 200, response.content)
        rows = response.json().get('results', response.json())
        for row in rows:
            user = row.get('user')
            if isinstance(user, dict):
                for field in ACCOUNT_ONLY:
                    self.assertNotIn(field, user)
