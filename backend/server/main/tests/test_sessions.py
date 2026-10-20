"""The cache-backed session store."""

from unittest import mock
from django.core.cache import cache
from django.test import TestCase


class SessionStoreTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_round_trip_and_database_fallback(self):
        from main.sessions import SessionStore

        store = SessionStore()
        store['k'] = 'v'
        store.create()
        key = store.session_key
        self.assertEqual(SessionStore(key)['k'], 'v')
        cache.clear()  # cold or restarted cache: the database still has it
        self.assertEqual(SessionStore(key)['k'], 'v')
        SessionStore(key).delete()
        self.assertIsNone(SessionStore(key).get('k'))

    def test_cached_copy_is_short_lived(self):
        from main.sessions import SessionStore

        store = SessionStore()
        store['k'] = 'v'
        with mock.patch.object(type(store._cache), 'set') as spy:
            store.create()
        ttls = [call.args[2] for call in spy.call_args_list if len(call.args) >= 3]
        self.assertTrue(ttls)
        self.assertLessEqual(max(ttls), 300)

    def test_a_cache_outage_does_not_break_sessions(self):
        from main.sessions import SessionStore

        store = SessionStore()
        store['k'] = 'v'
        store.create()
        key = store.session_key
        with mock.patch('django.core.cache.cache.get', side_effect=RuntimeError('down')):
            self.assertEqual(SessionStore(key)['k'], 'v')
