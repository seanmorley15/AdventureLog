from django.test import SimpleTestCase

from adventures.services.external_cache import build_cache_key


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
