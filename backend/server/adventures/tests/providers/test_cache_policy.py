"""Provider terms: Google results are never cached; OpenStreetMap lookups share one cache time."""

from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

LOCMEM = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'cache-policy'}}


def ok(json):
    response = MagicMock(status_code=200)
    response.json.return_value = json
    response.raise_for_status.return_value = None
    return response


@override_settings(CACHES=LOCMEM)
class GoogleIsNeverCachedTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_recommendations(self):
        from adventures.providers.recommendations import google

        with patch.object(google.requests, 'post', return_value=ok({'places': [{'id': 'x'}]})) as post:
            google.search_nearby(1.0, 2.0, 500, 'key', ['cafe'])
            google.search_nearby(1.0, 2.0, 500, 'key', ['cafe'])
        self.assertEqual(post.call_count, 2)

    def test_place_search_and_details(self):
        from adventures.providers.places import google

        with patch.object(google.requests, 'post', return_value=ok({'places': [{'id': 'x'}]})) as post:
            google.search_places('louvre', 'key')
            google.search_places('louvre', 'key')
        with patch.object(google.requests, 'get', return_value=ok({'id': 'x'})) as get:
            google.fetch_place_details('x', 'key')
            google.fetch_place_details('x', 'key')
        self.assertEqual((post.call_count, get.call_count), (2, 2))

    def test_reverse_geocode(self):
        from adventures.providers.geocoding import google

        payload = {'status': 'OK', 'results': [{'formatted_address': 'Paris'}]}
        with patch.object(google.requests, 'get', return_value=ok(payload)) as get:
            google.reverse_geocode(48.0, 2.0, 'key')
            google.reverse_geocode(48.0, 2.0, 'key')
        self.assertEqual(get.call_count, 2)


@override_settings(CACHES=LOCMEM)
class OsmCacheTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_every_osm_lookup_uses_the_one_setting(self):
        from adventures.providers.geocoding import osm as geocoding_osm
        from adventures.providers.places import osm as places_osm
        from adventures.providers.recommendations import osm as reco_osm
        from django.conf import settings

        self.assertEqual(settings.OSM_CACHE_TIMEOUT, 60 * 60 * 24)
        for module in (geocoding_osm, places_osm, reco_osm):
            self.assertEqual(module.OSM_CACHE_TIMEOUT, settings.OSM_CACHE_TIMEOUT, module.__name__)

    def test_overpass_answers_are_reused_including_empty_ones(self):
        from adventures.providers.recommendations import osm

        with patch.object(osm.requests, 'post', return_value=ok({'elements': []})) as post, \
                patch('core.cache.set_cached', wraps=__import__('core.cache', fromlist=['set_cached']).set_cached) as stored:
            osm.execute_overpass_query('[out:json];node(1);out;')
            osm.execute_overpass_query('[out:json];node(1);out;')
        self.assertEqual(post.call_count, 1)
        self.assertEqual(stored.call_args.kwargs['timeout'], 60 * 60 * 24)
