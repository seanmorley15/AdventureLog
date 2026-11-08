from unittest.mock import MagicMock, patch

import requests
from django.core.cache import cache
from django.test import SimpleTestCase

from adventures.providers.recommendations import osm


def ok():
    r = MagicMock(status_code=200)
    r.json.return_value = {'elements': []}
    return r


class OverpassMirrorTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        osm._mirror_unavailable_until.clear()

    def test_failed_mirror_is_skipped_on_the_next_search(self):
        calls = []

        def post(url, **kw):
            calls.append(url)
            if url == osm.OVERPASS_URLS[0]:
                raise requests.exceptions.ReadTimeout('slow')
            return ok()

        with patch.object(osm.requests, 'post', side_effect=post):
            self.assertIsNone(osm.execute_overpass_query('q1', timeout=5, max_mirrors=2).error)
            osm.execute_overpass_query('q2', timeout=5, max_mirrors=2)
        self.assertEqual(calls, [osm.OVERPASS_URLS[0], osm.OVERPASS_URLS[1], osm.OVERPASS_URLS[1]])

    def test_timeout_is_a_total_budget_across_mirrors(self):
        with patch.object(osm.requests, 'post', side_effect=requests.exceptions.ConnectTimeout('x')) as post:
            result = osm.execute_overpass_query('q3', timeout=5, max_mirrors=3)
        self.assertTrue(result.error)
        for call in post.call_args_list:
            connect, read = call.kwargs['timeout']
            self.assertLessEqual(read, 5)

    def test_all_mirrors_cooling_down_fails_fast(self):
        with patch.object(osm.requests, 'post', side_effect=requests.exceptions.ConnectTimeout('x')):
            osm.execute_overpass_query('q4', timeout=5)
        with patch.object(osm.requests, 'post') as post:
            self.assertTrue(osm.execute_overpass_query('q5', timeout=5).error)
        post.assert_not_called()
