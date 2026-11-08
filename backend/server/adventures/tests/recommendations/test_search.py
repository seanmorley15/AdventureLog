from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from adventures.services.recommendations.categories import get_category
from adventures.services.recommendations.search import build_overpass_query, get_recommendations
from core.errors import ServiceError
from core.results import ProviderResult

GOOGLE = 'adventures.services.recommendations.search.google_reco_provider.search_nearby'
OSM = 'adventures.services.recommendations.search.osm_reco_provider.execute_overpass_query'


def g_place(i, name=None):
    return {'id': f'g{i}', 'displayName': {'text': name or f'Place {i}'},
            'location': {'latitude': 48.0 + i * 0.001, 'longitude': 2.0}, 'types': ['restaurant'],
            'rating': 4.5, 'userRatingCount': 100, 'businessStatus': 'OPERATIONAL'}


OSM_DATA = {'elements': [{'type': 'node', 'id': 9, 'lat': 48.05, 'lon': 2.05,
                          'tags': {'name': 'OSM Diner', 'amenity': 'restaurant'}}]}


@override_settings(GOOGLE_MAPS_API_KEY='key')
class ProviderSelectionTests(SimpleTestCase):
    def run_search(self, **kw):
        return get_recommendations(48.0, 2.0, 5000, 'food', **kw)

    @patch(OSM)
    @patch(GOOGLE)
    def test_plentiful_google_skips_osm(self, google, osm):
        google.return_value = ProviderResult(data=[g_place(i) for i in range(10)])
        result = self.run_search()
        osm.assert_not_called()
        self.assertEqual(result['count'], 10)
        self.assertEqual(result['warnings'], [])

    @patch(OSM)
    @patch(GOOGLE)
    def test_sparse_google_is_topped_up_with_osm(self, google, osm):
        google.return_value = ProviderResult(data=[g_place(1)])
        osm.return_value = ProviderResult(data=OSM_DATA)
        result = self.run_search()
        self.assertEqual({r['source'] for r in result['results']}, {'google', 'osm'})
        self.assertEqual(result['sources_used']['osm'], 1)
        self.assertEqual(osm.call_args.kwargs['max_mirrors'], 2)

    @patch(OSM)
    @patch(GOOGLE)
    def test_osm_top_up_failure_only_warns(self, google, osm):
        google.return_value = ProviderResult(data=[g_place(1)])
        osm.return_value = ProviderResult(error='down')
        result = self.run_search()
        self.assertEqual(result['count'], 1)
        self.assertEqual(len(result['warnings']), 1)

    @patch(OSM)
    @patch(GOOGLE)
    def test_google_error_falls_back_to_osm_with_warning(self, google, osm):
        google.return_value = ProviderResult(error='boom')
        osm.return_value = ProviderResult(data=OSM_DATA)
        result = self.run_search()
        self.assertEqual(result['count'], 1)
        self.assertIn('Google Places: boom', result['warnings'])

    @patch(OSM)
    @patch(GOOGLE)
    def test_everything_failing_raises(self, google, osm):
        google.return_value = ProviderResult(error='boom')
        osm.return_value = ProviderResult(error='down')
        with self.assertRaises(ServiceError) as ctx:
            self.run_search()
        self.assertEqual(ctx.exception.status, 503)

    @patch(OSM)
    @patch(GOOGLE)
    def test_same_place_from_both_is_merged(self, google, osm):
        google.return_value = ProviderResult(data=[g_place(1, 'OSM Diner')])
        osm.return_value = ProviderResult(data={'elements': [{'type': 'node', 'id': 9, 'lat': 48.001, 'lon': 2.0,
                                                              'tags': {'name': 'OSM Diner', 'amenity': 'restaurant', 'website': 'https://d'}}]})
        result = self.run_search()
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['sources_used']['merged'], 1)
        self.assertEqual(result['results'][0]['website'], 'https://d')

    @patch(OSM)
    @patch(GOOGLE)
    def test_limit_and_ordering(self, google, osm):
        google.return_value = ProviderResult(data=[g_place(i) for i in range(12)])
        result = self.run_search(limit=5)
        scores = [r['quality_score'] for r in result['results']]
        self.assertEqual(len(scores), 5)
        self.assertEqual(scores, sorted(scores, reverse=True))

    @patch(GOOGLE)
    def test_google_only_without_key_is_not_configured(self, google):
        with override_settings(GOOGLE_MAPS_API_KEY=''):
            with self.assertRaises(ServiceError) as ctx:
                self.run_search(sources='google')
        self.assertEqual(ctx.exception.code, 'not_configured')
        google.assert_not_called()

    @patch(OSM)
    @patch(GOOGLE)
    def test_without_key_uses_osm_only(self, google, osm):
        osm.return_value = ProviderResult(data=OSM_DATA)
        with override_settings(GOOGLE_MAPS_API_KEY=''):
            result = self.run_search()
        google.assert_not_called()
        self.assertEqual(osm.call_args.kwargs['max_mirrors'], 3)
        self.assertEqual(result['count'], 1)

    def test_unknown_category(self):
        with self.assertRaises(ServiceError):
            get_recommendations(0, 0, 100, 'nope')

    @patch(OSM)
    @patch(GOOGLE)
    def test_alias_is_resolved(self, google, osm):
        google.return_value = ProviderResult(data=[g_place(i) for i in range(9)])
        result = get_recommendations(48.0, 2.0, 5000, 'tourism')
        self.assertEqual(result['category'], 'attractions')


class OverpassQueryTests(SimpleTestCase):
    def test_query_uses_every_selector_and_rounds_coordinates(self):
        query = build_overpass_query(get_category('culture'), 48.123456, 2.987654, 3000)
        self.assertIn('(around:3000,48.1235,2.9877)', query)
        self.assertIn('["tourism"~"^(museum|gallery)$"]', query)
        self.assertIn('["amenity"~"^(theatre|arts_centre)$"]', query)

    def test_radius_is_capped(self):
        self.assertIn('around:10000,', build_overpass_query(get_category('food'), 1, 1, 50000))
