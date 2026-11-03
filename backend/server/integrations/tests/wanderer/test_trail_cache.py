"""A Wanderer trail that failed is not asked for again on every page load."""

from unittest import mock
from django.core.cache import cache
from django.test import TestCase


class WandererFailureCacheTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_a_failed_trail_is_not_retried_every_time(self):
        from integrations.errors import IntegrationError
        from integrations.services import wanderer as ws

        integration = mock.Mock(id=7)
        with mock.patch.object(ws, 'make_wanderer_request', side_effect=IntegrationError('gone', status_code=404)) as request:
            for _ in range(3):
                with self.assertRaises(IntegrationError):
                    ws.fetch_trail_by_id(integration, 'abc')
        # Two detail paths are tried once; the next two calls are answered from the cache.
        self.assertEqual(request.call_count, len(ws.TRAIL_DETAIL_PATHS))

    def test_forcing_a_refresh_skips_the_failure_cache(self):
        from integrations.errors import IntegrationError
        from integrations.services import wanderer as ws

        integration = mock.Mock(id=8)
        cache.set(ws._failure_cache_key(8, 'abc'), {'message': 'gone', 'status_code': 404}, 60)
        with mock.patch.object(ws, 'make_wanderer_request', side_effect=IntegrationError('gone', status_code=404)) as request:
            with self.assertRaises(IntegrationError):
                ws.fetch_trail_by_id(integration, 'abc', use_cache=False)
        self.assertGreater(request.call_count, 0)
