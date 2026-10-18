import os
from datetime import date
from unittest import mock

from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APITestCase

from adventures.models import (
    Activity,
    Category,
    Collection,
    Location,
    Lodging,
    Note,
    Visit,
)
from adventures.providers.base import ProviderResult
from adventures.services.calendar_events import get_calendar_events_for_user
from adventures.services.external_cache import cached_provider, coordinate_key
from adventures.tests.test_collection_audience import make_user
from adventures.utils.geojson import cached_gpx_geojson
from adventures.utils.itinerary_days import convert_collection, get_day_by_index, place_object
from django.contrib.contenttypes.models import ContentType
from worldtravel.models import Country, Region, VisitedRegion

GPX = (
    b'<?xml version="1.0"?><gpx version="1.1" creator="t" xmlns="http://www.topografix.com/GPX/1/1">'
    b'<trk><name>Loop</name><trkseg><trkpt lat="1" lon="1"></trkpt><trkpt lat="1.1" lon="1.1"></trkpt>'
    b'</trkseg></trk></gpx>'
)


def count_queries(call):
    with CaptureQueriesContext(connection) as ctx:
        response = call()
    return len(ctx.captured_queries), response


class QueryCountTests(APITestCase):
    """Query counts stay flat as the amount of data grows."""

    def setUp(self):
        cache.clear()
        self.user = make_user('perf')
        self.client.force_authenticate(user=self.user)
        self.trip = Collection.objects.create(
            user=self.user, name='Trip', type='trip',
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 4),
        )
        convert_collection(self.trip)
        self.country = Country.objects.create(name='Norway', country_code='NO')
        self.region = Region.objects.create(id='NO-03', name='Oslo', country=self.country)

    def add_places(self, n, start=0):
        location_ct = ContentType.objects.get_for_model(Location)
        for i in range(start, start + n):
            category = Category.objects.get_or_create(
                user=self.user, name=f'cat{i % 3}', defaults={'display_name': f'Cat {i % 3}', 'icon': '*'}
            )[0]
            place = Location.objects.create(
                user=self.user, name=f'Place {i}', category=category,
                country=self.country, region=self.region,
            )
            place.collections.add(self.trip)
            Visit.objects.create(
                location=place,
                start_date=timezone.make_aware(timezone.datetime(2026, 6, 2)),
                end_date=timezone.make_aware(timezone.datetime(2026, 6, 2)),
            )
            place_object(self.trip, location_ct, place.id, day=get_day_by_index(self.trip, 1 + i % 3))
            Lodging.objects.create(user=self.user, name=f'Stay {i}', collection=self.trip)
            Note.objects.create(user=self.user, name=f'Note {i}', collection=self.trip)

    def get(self, url, **params):
        return self.client.get(url, params)

    def assert_flat(self, url, label, slack=3, **params):
        self.add_places(4)
        small, response = count_queries(lambda: self.get(url, **params))
        self.assertEqual(response.status_code, 200, label)
        self.add_places(12, start=4)
        large, response = count_queries(lambda: self.get(url, **params))
        self.assertEqual(response.status_code, 200, label)
        self.assertLessEqual(large, small + slack, f'{label}: {small} queries for 4 places, {large} for 16')
        return large

    def test_collection_detail_does_not_grow_with_places(self):
        self.assert_flat(f'/api/collections/{self.trip.id}/', 'collection detail')

    def test_story_does_not_grow_with_places(self):
        self.trip.visibility = 'public'
        self.trip.save()
        self.client.force_authenticate(user=None)
        self.assert_flat(f'/api/collections/{self.trip.id}/', 'story')

    def test_location_list_all_and_pins_do_not_grow(self):
        self.assert_flat('/api/locations/', 'locations list')
        self.assert_flat('/api/locations/all/', 'locations all', include_collections='true')
        self.assert_flat('/api/locations/pins/', 'pins')

    def test_collection_lists_do_not_grow_with_collections(self):
        def make(n, start):
            for i in range(start, start + n):
                c = Collection.objects.create(user=self.user, name=f'C{i}', type='trip')
                convert_collection(c)
                c.shared_with.add(make_user(f'friend{i}'))
        make(3, 0)
        small, _ = count_queries(lambda: self.get('/api/collections/'))
        make(9, 3)
        large, response = count_queries(lambda: self.get('/api/collections/'))
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(large, small + 3, f'{small} vs {large}')

    def test_calendar_does_not_grow(self):
        self.assert_flat('/api/calendar/events/', 'calendar')

    def test_categories_do_not_grow(self):
        self.assert_flat('/api/categories/', 'categories')

    def test_world_travel_counts_match_and_do_not_grow(self):
        for i in range(3):
            region = Region.objects.create(id=f'NO-{50 + i}', name=f'R{i}', country=self.country)
            VisitedRegion.objects.create(user=self.user, region=region)
        data = self.get('/api/countries/').json()
        results = data['results'] if isinstance(data, dict) and 'results' in data else data
        norway = next(c for c in results if c['country_code'] == 'NO')
        self.assertEqual(norway['num_regions'], Region.objects.filter(country=self.country).count())
        self.assertEqual(norway['num_visits'], 3)
        for i in range(30):
            Country.objects.create(name=f'Land {i}', country_code=f'{chr(65 + i // 26)}{chr(65 + i % 26)}'.replace('NO', 'NX'))
        n, _ = count_queries(lambda: self.get('/api/countries/'))
        self.assertLessEqual(n, 6)


class CurrentUserCountsTests(APITestCase):
    def test_current_user_returns_badge_counts(self):
        user = make_user('badge')
        owner = make_user('badge-owner')
        trip = Collection.objects.create(user=owner, name='Shared')
        from adventures.models import CollectionInvite

        CollectionInvite.objects.create(collection=trip, invited_user=user)
        self.client.force_authenticate(user=user)
        body = self.client.get('/auth/current-user/').json()
        self.assertEqual(body['pending_invite_count'], 1)
        self.assertEqual(body['unread_comment_count'], 0)


class GpxCacheTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user('gpx')
        self.day = None

    def activity(self, content=GPX, name='track.gpx'):
        trip = Collection.objects.create(user=self.user, name='G', type='trip')
        convert_collection(trip)
        from adventures.utils.itinerary_days import build_days

        build_days(trip, 1)
        day = trip.itinerary_days.first()
        activity = Activity(user=self.user, day=day, name='Run')
        activity.gpx_file.save(name, ContentFile(content), save=True)
        return activity

    def test_second_call_does_not_parse_the_file(self):
        activity = self.activity()
        with mock.patch('adventures.utils.geojson.gpx_to_geojson', wraps=__import__('adventures.utils.geojson', fromlist=['x']).gpx_to_geojson) as spy:
            first = cached_gpx_geojson(activity.gpx_file)
            second = cached_gpx_geojson(activity.gpx_file)
        self.assertEqual(first, second)
        self.assertEqual(spy.call_count, 1)
        self.assertEqual(first['features'][0]['properties']['name'], 'Loop')

    def test_errors_are_not_cached(self):
        activity = self.activity(content=b'not xml', name='bad.gpx')
        with mock.patch('adventures.utils.geojson.gpx_to_geojson', return_value={'error': 'x'}) as spy:
            cached_gpx_geojson(activity.gpx_file)
            cached_gpx_geojson(activity.gpx_file)
        self.assertEqual(spy.call_count, 2)

    def test_a_cache_failure_falls_back_to_parsing(self):
        activity = self.activity()
        with mock.patch('django.core.cache.cache.get', side_effect=RuntimeError('down')), \
                mock.patch('django.core.cache.cache.set', side_effect=RuntimeError('too large')):
            result = cached_gpx_geojson(activity.gpx_file)
        self.assertEqual(result['type'], 'FeatureCollection')


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


class WandererFailureCacheTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_a_failed_trail_is_not_retried_every_time(self):
        from integrations import wanderer_services as ws

        integration = mock.Mock(id=7)
        with mock.patch.object(ws, 'make_wanderer_request', side_effect=ws.IntegrationError('gone', status_code=404)) as request:
            for _ in range(3):
                with self.assertRaises(ws.IntegrationError):
                    ws.fetch_trail_by_id(integration, 'abc')
        # Two detail paths are tried once; the next two calls are answered from the cache.
        self.assertEqual(request.call_count, len(ws.TRAIL_DETAIL_PATHS))

    def test_forcing_a_refresh_skips_the_failure_cache(self):
        from integrations import wanderer_services as ws

        integration = mock.Mock(id=8)
        cache.set(ws._failure_cache_key(8, 'abc'), {'message': 'gone', 'status_code': 404}, 60)
        with mock.patch.object(ws, 'make_wanderer_request', side_effect=ws.IntegrationError('gone', status_code=404)) as request:
            with self.assertRaises(ws.IntegrationError):
                ws.fetch_trail_by_id(integration, 'abc', use_cache=False)
        self.assertGreater(request.call_count, 0)


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
