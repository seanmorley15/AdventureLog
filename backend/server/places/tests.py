"""Tests for the places app: cache normalization/hit/miss/TTL and the
nearby-places endpoint (ownership, missing/invalid params). Overpass itself
is always mocked — these tests must never make a real network call.
"""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from adventures.models import Location

from .models import OverpassCacheEntry
from .services import get_nearby_places, normalize_query_key

User = get_user_model()

FAKE_RESULT = {
    'error': None,
    'results': [
        {'id': 'osm:node:1', 'name': 'Trattoria Roma', 'latitude': 41.9, 'longitude': 12.5},
    ],
}


class NormalizeQueryKeyTests(TestCase):
    def test_same_search_different_param_order_same_key(self):
        key_a = normalize_query_key(lat=41.9028, lon=12.4964, radius=2000, category='food')
        key_b = normalize_query_key(lon=12.4964, lat=41.9028, category='food', radius=2000)
        self.assertEqual(key_a, key_b)

    def test_different_category_different_key(self):
        key_food = normalize_query_key(lat=41.9028, lon=12.4964, radius=2000, category='food')
        key_tourism = normalize_query_key(lat=41.9028, lon=12.4964, radius=2000, category='tourism')
        self.assertNotEqual(key_food, key_tourism)

    def test_coordinates_rounded_so_near_identical_points_collide(self):
        key_a = normalize_query_key(lat=41.90281, lon=12.49641, radius=2000, category='food')
        key_b = normalize_query_key(lat=41.90282, lon=12.49642, radius=2000, category='food')
        self.assertEqual(key_a, key_b)


class GetNearbyPlacesCacheTests(TestCase):
    @patch('places.services.overpass_client.fetch_nearby')
    def test_repeated_identical_search_hits_overpass_only_once(self, mock_fetch):
        mock_fetch.return_value = FAKE_RESULT

        first = get_nearby_places(41.9028, 12.4964, 2000, 'food')
        second = get_nearby_places(41.9028, 12.4964, 2000, 'food')

        self.assertEqual(mock_fetch.call_count, 1)
        self.assertFalse(first['cached'])
        self.assertTrue(second['cached'])
        self.assertEqual(second['results'], FAKE_RESULT['results'])

    @patch('places.services.overpass_client.fetch_nearby')
    def test_expired_ttl_hits_overpass_again(self, mock_fetch):
        mock_fetch.return_value = FAKE_RESULT

        get_nearby_places(41.9028, 12.4964, 2000, 'food')
        OverpassCacheEntry.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        get_nearby_places(41.9028, 12.4964, 2000, 'food')

        self.assertEqual(mock_fetch.call_count, 2)

    @patch('places.services.overpass_client.fetch_nearby')
    def test_error_responses_are_not_cached(self, mock_fetch):
        mock_fetch.return_value = {'error': 'OpenStreetMap temporarily unavailable.', 'results': []}

        get_nearby_places(41.9028, 12.4964, 2000, 'food')
        get_nearby_places(41.9028, 12.4964, 2000, 'food')

        self.assertEqual(mock_fetch.call_count, 2)
        self.assertEqual(OverpassCacheEntry.objects.count(), 0)


class NearbyPlacesViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', email='owner@example.com', password='pw12345!')
        self.other = User.objects.create_user(username='other', email='other@example.com', password='pw12345!')
        self.location = Location.objects.create(user=self.owner, name='Colosseo', latitude=41.9028, longitude=12.4964)
        self.client = APIClient()

    @patch('places.views.services.get_nearby_places')
    def test_owner_gets_200(self, mock_get):
        mock_get.return_value = {'error': None, 'results': FAKE_RESULT['results'], 'cached': False}
        self.client.force_authenticate(self.owner)

        response = self.client.get('/api/places/nearby/', {'stop': self.location.id, 'category': 'food'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

    def test_non_owner_gets_403(self):
        self.client.force_authenticate(self.other)

        response = self.client.get('/api/places/nearby/', {'stop': self.location.id, 'category': 'food'})

        self.assertEqual(response.status_code, 403)

    def test_invalid_category_gets_400(self):
        self.client.force_authenticate(self.owner)

        response = self.client.get('/api/places/nearby/', {'stop': self.location.id, 'category': 'invalid'})

        self.assertEqual(response.status_code, 400)

    def test_missing_stop_gets_400(self):
        self.client.force_authenticate(self.owner)

        response = self.client.get('/api/places/nearby/', {'category': 'food'})

        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_gets_401_or_403(self):
        response = self.client.get('/api/places/nearby/', {'stop': self.location.id, 'category': 'food'})

        self.assertIn(response.status_code, (401, 403))
