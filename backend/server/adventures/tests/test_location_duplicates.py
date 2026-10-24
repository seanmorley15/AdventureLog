from rest_framework.test import APITestCase

from adventures.models import Location, Visit
from adventures.services.locations.duplicates import (
    find_duplicate_locations,
    name_similarity,
    token_jaccard,
)
from adventures.utils.geo import make_point
from users.models import CustomUser


class LocationDuplicateMatchingTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='dup-user',
            email='dup-user@example.com',
            password='testpassword123',
        )
        self.other_user = CustomUser.objects.create_user(
            username='other-dup-user',
            email='other-dup-user@example.com',
            password='testpassword123',
        )

    def _create_location(self, user, name, lat=None, lon=None, location=None):
        return Location.objects.create(
            user=user,
            name=name,
            location=location,
            coordinates=make_point(lon, lat) if lat is not None and lon is not None else None,
        )

    def test_saint_peter_name_variants_match(self):
        existing = self._create_location(
            self.user,
            "Church of Saint Peter",
            51.5138,
            -0.0984,
            'City of London',
        )

        matches = find_duplicate_locations(
            self.user,
            name="St Peter's Church",
            latitude=51.5139,
            longitude=-0.0983,
            location='City of London',
        )

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].location.id, existing.id)
        self.assertIn('similar_name', matches[0].reasons)

    def test_name_variants_match_without_coordinates(self):
        existing = self._create_location(self.user, "Church of Saint Peter")

        matches = find_duplicate_locations(self.user, name="St Peter's Church")

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].location.id, existing.id)
        self.assertGreaterEqual(token_jaccard("St Peter's Church", existing.name), 0.75)
        self.assertGreaterEqual(name_similarity("St Peter's Church", existing.name), 0.7)

    def test_same_coordinates_are_duplicates(self):
        existing = self._create_location(self.user, 'Old Mill Cafe', 40.7580, -73.9855)

        matches = find_duplicate_locations(
            self.user,
            name='Coffee Shop',
            latitude=40.7580,
            longitude=-73.9855,
        )

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].location.id, existing.id)
        self.assertIn('nearby_coordinates', matches[0].reasons)

    def test_same_name_far_apart_is_not_a_duplicate(self):
        self._create_location(self.user, "McDonald's", 40.7580, -73.9855)

        matches = find_duplicate_locations(
            self.user,
            name="McDonald's",
            latitude=34.0522,
            longitude=-118.2437,
        )

        self.assertEqual(matches, [])

    def test_does_not_match_other_users_locations(self):
        self._create_location(self.other_user, "St Peter's Church", 51.5138, -0.0984)

        matches = find_duplicate_locations(
            self.user,
            name="St Peter's Church",
            latitude=51.5138,
            longitude=-0.0984,
        )

        self.assertEqual(matches, [])

    def test_exclude_id_skips_the_location_being_edited(self):
        existing = self._create_location(self.user, 'Central Park', 40.7829, -73.9654)

        matches = find_duplicate_locations(
            self.user,
            name='Central Park',
            latitude=40.7829,
            longitude=-73.9654,
            exclude_id=existing.id,
        )

        self.assertEqual(matches, [])

    def test_partial_name_matches_longer_existing_name(self):
        existing = self._create_location(self.user, "Church of Saint Peter")

        matches = find_duplicate_locations(self.user, name='St Peter')

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].location.id, existing.id)

    def test_nested_park_name_matches_without_coordinates(self):
        existing = self._create_location(self.user, 'Yosemite National Park')

        matches = find_duplicate_locations(self.user, name='Yosemite')

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].location.id, existing.id)

    def test_short_saint_token_does_not_match_every_church(self):
        self._create_location(self.user, "Church of Saint Peter")

        matches = find_duplicate_locations(self.user, name='St')

        self.assertEqual(matches, [])

    def test_nearby_pin_matches_without_a_useful_name(self):
        existing = self._create_location(self.user, 'Old Mill Cafe', 40.7580, -73.9855)

        matches = find_duplicate_locations(
            self.user,
            name='',
            latitude=40.7581,
            longitude=-73.9854,
        )

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].location.id, existing.id)
        self.assertIn('nearby_coordinates', matches[0].reasons)


class LocationDuplicateApiTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='dup-api-user',
            email='dup-api-user@example.com',
            password='testpassword123',
        )
        self.client.force_authenticate(user=self.user)
        self.existing = Location.objects.create(
            user=self.user,
            name="Church of Saint Peter",
            location='City of London',
            coordinates=make_point(-0.0984, 51.5138),
        )
        Visit.objects.create(location=self.existing)

    def test_check_duplicates_returns_matches(self):
        response = self.client.post(
            '/api/locations/check-duplicates/',
            {
                'name': "St Peter's Church",
                'latitude': 51.5139,
                'longitude': -0.0983,
                'location': 'City of London',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        matches = response.json()['matches']
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['id'], str(self.existing.id))
        self.assertEqual(matches[0]['name'], "Church of Saint Peter")
        self.assertGreaterEqual(matches[0]['visit_count'], 1)
        self.assertIn('similar_name', matches[0]['reasons'])

    def test_check_duplicates_requires_name_or_coordinates(self):
        response = self.client.post(
            '/api/locations/check-duplicates/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'error': 'name or coordinates are required'})

    def test_check_duplicates_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            '/api/locations/check-duplicates/',
            {'name': "St Peter's Church"},
            format='json',
        )

        self.assertIn(response.status_code, (401, 403))
