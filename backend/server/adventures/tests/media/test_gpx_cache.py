"""GPX files are parsed once and the result is cached."""

from unittest import mock
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.test import TestCase
from adventures.models import Activity, Collection
from adventures.tests.base import make_user
from adventures.utils.geojson import cached_gpx_geojson
from adventures.services.day_plan import convert_collection


GPX = (
    b'<?xml version="1.0"?><gpx version="1.1" creator="t" xmlns="http://www.topografix.com/GPX/1/1">'
    b'<trk><name>Loop</name><trkseg><trkpt lat="1" lon="1"></trkpt><trkpt lat="1.1" lon="1.1"></trkpt>'
    b'</trkseg></trk></gpx>'
)


class GpxCacheTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user('gpx')
        self.day = None

    def activity(self, content=GPX, name='track.gpx'):
        trip = Collection.objects.create(user=self.user, name='G', type='trip')
        convert_collection(trip)
        from adventures.services.day_plan import build_days

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
