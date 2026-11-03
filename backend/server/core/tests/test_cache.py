from django.core.cache import cache
from django.test import TestCase
from core.results import ProviderResult
from core.cache import cached_provider, coordinate_key
from django.test import SimpleTestCase

from core.cache import build_cache_key


class ExternalCacheKeyTests(SimpleTestCase):
    def test_spaces_are_sanitized_for_memcached(self):
        key = build_cache_key('wikipedia_desc_v1', 'en', 'Acadia National Park')
        self.assertEqual(key, 'wikipedia_desc_v1:en:acadia_national_park')
        self.assertNotIn(' ', key)

    def test_empty_parts_are_omitted(self):
        key = build_cache_key('wikipedia_summary_v1', 'en', '  ')
        self.assertEqual(key, 'wikipedia_summary_v1:en')

    def test_long_keys_are_hashed(self):
        long_name = 'a' * 250
        key = build_cache_key('wikipedia_desc_v1', 'en', long_name)
        self.assertTrue(key.startswith('wikipedia_desc_v1:'))
        self.assertLessEqual(len(key), 200)


class ProviderCacheTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_success_is_cached_and_shared_error_is_not(self):
        calls = []

        @cached_provider('test_provider', lambda q, api_key=None: (q,), 60)
        def lookup(q, api_key=None):
            calls.append(api_key)
            return ProviderResult(data={'q': q}) if q != 'bad' else ProviderResult(error='boom')

        self.assertEqual(lookup('a', api_key='key-one').data, {'q': 'a'})
        # A different API key hits the same entry: the key is not part of the cache key.
        self.assertEqual(lookup('a', api_key='key-two').data, {'q': 'a'})
        self.assertEqual(calls, ['key-one'])
        lookup('bad')
        lookup('bad')
        self.assertEqual(calls.count(None), 2)

    def test_coordinates_round_for_keys(self):
        self.assertEqual(coordinate_key(40.7128001, 5), coordinate_key(40.7128004, 5))
        self.assertNotEqual(coordinate_key(40.7128, 5), coordinate_key(40.7138, 5))
