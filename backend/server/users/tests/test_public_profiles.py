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


class PublicProfileListingTests(APITestCase):
    """The pieces the profile page loads: slim paged locations, map pins and public-only counts."""

    def setUp(self):
        from django.contrib.gis.geos import Point

        from adventures.models import Location

        self.person = CustomUser.objects.create_user(
            username='lister', email='lister@example.com', password='testpassword123', public_profile=True
        )
        self.viewer = CustomUser.objects.create_user(
            username='looker', email='looker@example.com', password='testpassword123'
        )
        for i in range(3):
            Location.objects.create(
                user=self.person, name=f'Public {i}', is_public=True, coordinates=Point(20 + i, 10 + i, srid=4326)
            )
        Location.objects.create(user=self.person, name='Secret', is_public=False, coordinates=Point(2, 1, srid=4326))
        Location.objects.create(user=self.person, name='No coords', is_public=True)

    def test_locations_are_public_only_and_paginated(self):
        response = self.client.get(f'/api/users/{self.person.username}/locations/?page_size=2')

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['count'], 4)
        self.assertEqual(len(body['results']), 2)
        self.assertNotIn('Secret', [r['name'] for r in body['results']])
        self.assertNotIn('visits', body['results'][0])

    def test_locations_can_be_ordered_by_name(self):
        response = self.client.get(f'/api/users/{self.person.username}/locations/?ordering=name')

        names = [r['name'] for r in response.json()['results']]
        self.assertEqual(names, sorted(names))

    def test_pins_skip_private_and_coordinate_less_locations(self):
        response = self.client.get(f'/api/users/{self.person.username}/pins/')

        self.assertEqual(response.status_code, 200)
        pins = sorted(response.json(), key=lambda p: p['name'])
        self.assertEqual([p['name'] for p in pins], ['Public 0', 'Public 1', 'Public 2'])
        self.assertEqual((pins[0]['latitude'], pins[0]['longitude']), (10.0, 20.0))

    def test_detail_can_leave_locations_out(self):
        response = self.client.get(f'/api/users/{self.person.username}/?locations=false')

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('locations', response.json())
        self.assertIn('collections', response.json())

    def test_stats_count_only_what_is_public_for_other_people(self):
        theirs = self.client.get(f'/api/users/{self.person.username}/stats/').json()
        self.assertEqual(theirs['location_count'], 4)

        self.client.force_authenticate(user=self.person)
        own = self.client.get(f'/api/users/{self.person.username}/stats/').json()
        self.assertEqual(own['location_count'], 5)

    def test_private_profile_is_404_for_the_new_endpoints(self):
        hidden = CustomUser.objects.create_user(
            username='hidden', email='hidden@example.com', password='testpassword123'
        )
        for path in ('locations', 'pins'):
            self.assertEqual(self.client.get(f'/api/users/{hidden.username}/{path}/').status_code, 404)
