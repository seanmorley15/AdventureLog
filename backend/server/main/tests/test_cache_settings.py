"""Which cache backend the settings choose."""

import os
from unittest import mock
from django.test import TestCase


class CacheSettingsTests(TestCase):
    def build(self, **env):
        from main import settings as app_settings

        with mock.patch.dict(os.environ, env, clear=False):
            return app_settings._build_caches()['default']

    def test_default_is_memcached_with_resilient_options(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('CACHE_BACKEND', None)
            config = self.build()
        self.assertTrue(config['BACKEND'].endswith('PyMemcacheCache'))
        self.assertEqual(config['LOCATION'], os.environ.get('MEMCACHED_LOCATION', '127.0.0.1:11211'))
        self.assertTrue(config['OPTIONS']['ignore_exc'])

    def test_redis_is_chosen_by_env(self):
        config = self.build(CACHE_BACKEND='redis', REDIS_URL='redis://cache:6379/2', CACHE_KEY_PREFIX='al')
        self.assertEqual(config['BACKEND'], 'django.core.cache.backends.redis.RedisCache')
        self.assertEqual(config['LOCATION'], 'redis://cache:6379/2')
        self.assertEqual(config['KEY_PREFIX'], 'al')

    def test_locmem_dummy_and_unknown_values(self):
        self.assertTrue(self.build(CACHE_BACKEND='locmem')['BACKEND'].endswith('LocMemCache'))
        self.assertTrue(self.build(CACHE_BACKEND='dummy')['BACKEND'].endswith('DummyCache'))
        self.assertTrue(self.build(CACHE_BACKEND='bogus')['BACKEND'].endswith('PyMemcacheCache'))
