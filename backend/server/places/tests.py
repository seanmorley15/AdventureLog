"""Tests for the places app: cache normalization/hit/miss/TTL, the
nearby-places endpoint (ownership, missing/invalid params), and the P5b LLM
ranking pipeline (anti-hallucination guard-rail, I1). Overpass and the LLM
are always mocked — these tests must never make a real network call.
"""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from adventures.models import Location
from routing.exceptions import OSRMUnavailableError

from . import ranking
from .exceptions import LLMUnavailableError
from .models import OverpassCacheEntry
from .services import get_nearby_places, normalize_query_key

User = get_user_model()

FAKE_RESULT = {
    'error': None,
    'results': [
        {'id': 'osm:node:1', 'name': 'Trattoria Roma', 'latitude': 41.9, 'longitude': 12.5},
    ],
}

FAKE_CANDIDATES = [
    {
        'id': 'osm:node:1',
        'name': 'Trattoria Roma',
        'latitude': 41.9028,
        'longitude': 12.4964,
        'primary_type': 'restaurant',
        'cuisine': 'italian',
        'wheelchair': 'yes',
        'fee': None,
        'opening_hours': 'Mo-Su 12:00-23:00',
        'description': None,
    },
    {
        'id': 'osm:node:2',
        'name': 'Pizzeria da Fome',
        'latitude': 41.9,
        'longitude': 12.49,
        'primary_type': 'restaurant',
        'cuisine': 'pizza',
        'wheelchair': None,
        'fee': None,
        'opening_hours': None,
        'description': None,
    },
]


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


class SanitizeCandidateTests(TestCase):
    """Guard-rail I1, part 1: the LLM must never receive a geospatial fact."""

    def test_sanitized_candidate_excludes_geospatial_fields(self):
        sanitized = ranking._sanitize_candidate(FAKE_CANDIDATES[0])

        self.assertNotIn('latitude', sanitized)
        self.assertNotIn('longitude', sanitized)
        self.assertNotIn('distance_km', sanitized)
        self.assertNotIn('address', sanitized)
        self.assertEqual(sanitized['id'], 'osm:node:1')
        self.assertEqual(sanitized['category'], 'restaurant')
        self.assertEqual(sanitized['cuisine'], 'italian')


class SuggestPlacesPipelineTests(TestCase):
    """Guard-rail I1, part 2: every id the pipeline returns must trace back
    to a real Overpass candidate — a fake id from the LLM is discarded."""

    def setUp(self):
        self.owner = User.objects.create_user(username='owner2', email='owner2@example.com', password='pw12345!')
        self.location = Location.objects.create(
            user=self.owner, name='Colosseo', latitude=41.9028, longitude=12.4964
        )

    @patch('places.ranking.osrm_client.get_duration_matrix')
    @patch('places.ranking.llm_client.rank_candidates')
    @patch('places.ranking.services.get_nearby_places')
    def test_hallucinated_id_is_discarded(self, mock_get_nearby, mock_rank, mock_osrm):
        mock_get_nearby.return_value = {'error': None, 'results': FAKE_CANDIDATES, 'cached': False}
        mock_rank.return_value = [{'id': 'osm:node:DOES-NOT-EXIST', 'justification': 'Lugar inventado.'}]
        mock_osrm.return_value = [[0, 100, 200], [100, 0, 50], [200, 50, 0]]

        result = ranking.suggest_places(self.location, 'food', 2000, '')

        self.assertIsNone(result['error'])
        self.assertEqual(result['suggestions'], [])

    @patch('places.ranking.osrm_client.get_duration_matrix')
    @patch('places.ranking.llm_client.rank_candidates')
    @patch('places.ranking.services.get_nearby_places')
    def test_valid_id_is_kept_with_justification_and_travel_time(self, mock_get_nearby, mock_rank, mock_osrm):
        mock_get_nearby.return_value = {'error': None, 'results': FAKE_CANDIDATES, 'cached': False}
        mock_rank.return_value = [{'id': 'osm:node:1', 'justification': 'Boa opção italiana.'}]
        mock_osrm.return_value = [[0, 300], [300, 0]]

        result = ranking.suggest_places(self.location, 'food', 2000, 'vegetariano')

        self.assertIsNone(result['error'])
        self.assertEqual(len(result['suggestions']), 1)
        suggestion = result['suggestions'][0]
        self.assertEqual(suggestion['id'], 'osm:node:1')
        self.assertEqual(suggestion['justification'], 'Boa opção italiana.')
        self.assertEqual(suggestion['travel_seconds'], 300)

    @patch('places.ranking.llm_client.rank_candidates')
    @patch('places.ranking.services.get_nearby_places')
    def test_mixed_valid_and_hallucinated_ids_only_keeps_the_real_one(self, mock_get_nearby, mock_rank):
        mock_get_nearby.return_value = {'error': None, 'results': FAKE_CANDIDATES, 'cached': False}
        mock_rank.return_value = [
            {'id': 'osm:node:2', 'justification': 'Pizza rápida.'},
            {'id': 'osm:node:FAKE', 'justification': 'Não existe.'},
        ]

        with patch('places.ranking.osrm_client.get_duration_matrix', side_effect=OSRMUnavailableError('down')):
            result = ranking.suggest_places(self.location, 'food', 2000, '')

        self.assertEqual([s['id'] for s in result['suggestions']], ['osm:node:2'])
        # OSRM indisponível degrada graciosamente (I4) — sem travel_seconds, sem 500.
        self.assertIsNone(result['suggestions'][0]['travel_seconds'])

    @patch('places.ranking.llm_client.rank_candidates')
    @patch('places.ranking.services.get_nearby_places')
    def test_llm_unavailable_returns_controlled_error(self, mock_get_nearby, mock_rank):
        mock_get_nearby.return_value = {'error': None, 'results': FAKE_CANDIDATES, 'cached': False}
        mock_rank.side_effect = LLMUnavailableError('LLM_API_KEY não configurada')

        result = ranking.suggest_places(self.location, 'food', 2000, '')

        self.assertEqual(result['error'], 'LLM_API_KEY não configurada')
        self.assertEqual(result['suggestions'], [])
        mock_rank.assert_called_once()

    @patch('places.ranking.llm_client.rank_candidates')
    @patch('places.ranking.services.get_nearby_places')
    def test_no_candidates_never_calls_the_llm(self, mock_get_nearby, mock_rank):
        mock_get_nearby.return_value = {'error': None, 'results': [], 'cached': False}

        result = ranking.suggest_places(self.location, 'food', 2000, '')

        self.assertEqual(result, {'error': None, 'suggestions': []})
        mock_rank.assert_not_called()


class SuggestPlacesViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner3', email='owner3@example.com', password='pw12345!')
        self.other = User.objects.create_user(username='other3', email='other3@example.com', password='pw12345!')
        self.location = Location.objects.create(user=self.owner, name='Colosseo', latitude=41.9028, longitude=12.4964)
        self.client = APIClient()

    @patch('places.views.ranking.suggest_places')
    def test_owner_gets_200(self, mock_suggest):
        mock_suggest.return_value = {
            'error': None,
            'suggestions': [{**FAKE_CANDIDATES[0], 'justification': 'ok', 'travel_seconds': 120}],
        }
        self.client.force_authenticate(self.owner)

        response = self.client.post(
            '/api/places/suggest/', {'stop': self.location.id, 'category': 'food', 'restrictions': 'sem glúten'}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

    def test_non_owner_gets_403(self):
        self.client.force_authenticate(self.other)

        response = self.client.post('/api/places/suggest/', {'stop': self.location.id, 'category': 'food'})

        self.assertEqual(response.status_code, 403)

    def test_invalid_category_gets_400(self):
        self.client.force_authenticate(self.owner)

        response = self.client.post('/api/places/suggest/', {'stop': self.location.id, 'category': 'invalid'})

        self.assertEqual(response.status_code, 400)

    def test_missing_stop_gets_400(self):
        self.client.force_authenticate(self.owner)

        response = self.client.post('/api/places/suggest/', {'category': 'food'})

        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_gets_401_or_403(self):
        response = self.client.post('/api/places/suggest/', {'stop': self.location.id, 'category': 'food'})

        self.assertIn(response.status_code, (401, 403))

    @patch('places.views.ranking.suggest_places')
    def test_llm_unavailable_gets_503(self, mock_suggest):
        mock_suggest.return_value = {'error': 'LLM_API_KEY não configurada', 'suggestions': []}
        self.client.force_authenticate(self.owner)

        response = self.client.post('/api/places/suggest/', {'stop': self.location.id, 'category': 'food'})

        self.assertEqual(response.status_code, 503)
