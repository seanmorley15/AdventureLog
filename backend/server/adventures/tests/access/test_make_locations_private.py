"""The owner can make every location in a collection private in one step."""

from rest_framework.test import APITestCase

from adventures.models import Collection, Location
from users.models import CustomUser


class MakeLocationsPrivateTests(APITestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='mlp-owner', email='mlp-owner@example.com', password='testpassword123'
        )
        self.member = CustomUser.objects.create_user(
            username='mlp-member', email='mlp-member@example.com', password='testpassword123'
        )
        self.collection = Collection.objects.create(user=self.owner, name='Road trip')
        self.collection.shared_with.add(self.member)

        self.public_one = Location.objects.create(user=self.owner, name='Public one', is_public=True)
        self.public_two = Location.objects.create(user=self.owner, name='Public two', is_public=True)
        self.already_private = Location.objects.create(user=self.owner, name='Private', is_public=False)
        self.members_place = Location.objects.create(user=self.member, name='Member spot', is_public=True)
        self.elsewhere = Location.objects.create(user=self.owner, name='Not linked', is_public=True)
        for place in (self.public_one, self.public_two, self.already_private, self.members_place):
            place.collections.add(self.collection)

        self.url = f'/api/collections/{self.collection.id}/make-locations-private/'

    def test_owner_turns_off_their_linked_public_locations(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body['updated'], 2)
        self.assertCountEqual(body['location_ids'], [str(self.public_one.id), str(self.public_two.id)])
        for place in (self.public_one, self.public_two):
            place.refresh_from_db()
            self.assertFalse(place.is_public)

    def test_member_locations_and_unlinked_locations_stay_public(self):
        self.client.force_authenticate(user=self.owner)

        self.client.post(self.url)

        self.members_place.refresh_from_db()
        self.elsewhere.refresh_from_db()
        self.assertTrue(self.members_place.is_public)
        self.assertTrue(self.elsewhere.is_public)

    def test_running_it_again_changes_nothing(self):
        self.client.force_authenticate(user=self.owner)
        self.client.post(self.url)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {'updated': 0, 'location_ids': []})

    def test_a_member_cannot_do_it(self):
        self.client.force_authenticate(user=self.member)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 404, response.content)
        self.public_one.refresh_from_db()
        self.assertTrue(self.public_one.is_public)

    def test_anonymous_cannot_do_it(self):
        response = self.client.post(self.url)

        self.assertIn(response.status_code, (401, 403, 404), response.content)
        self.public_one.refresh_from_db()
        self.assertTrue(self.public_one.is_public)
