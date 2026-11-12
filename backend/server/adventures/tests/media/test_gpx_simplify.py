"""GPX tracks are drawn on maps, so they are sent at map resolution, not recording resolution (#1164)."""

import math
import shutil
import tempfile

from django.core.cache import cache
from django.core.files.base import ContentFile
from django.test import SimpleTestCase, TestCase, override_settings

from adventures.models import Collection, ContentAttachment, Transportation
from adventures.tests.base import make_user
from adventures.utils.geojson import MAX_TRACK_POINTS, gpx_bytes_to_geojson


def gpx(points, name='Hike'):
    trkpts = ''.join(f'<trkpt lat="{lat}" lon="{lon}"></trkpt>' for lon, lat in points)
    return (
        '<?xml version="1.0"?><gpx version="1.1" creator="t" xmlns="http://www.topografix.com/GPX/1/1">'
        f'<trk><name>{name}</name><trkseg>{trkpts}</trkseg></trk></gpx>'
    ).encode()


def recorded_hike(count):
    """A winding track sampled every metre or so, like a watch recording once a second."""
    return [
        (2.1 + i * 0.00001, 41.4 + 0.002 * math.sin(i / 400))
        for i in range(count)
    ]


def coordinates(result):
    return [c for feature in result['features'] for c in feature['geometry']['coordinates']]


class GpxSimplifyTests(SimpleTestCase):
    def test_a_long_recording_is_reduced_to_map_resolution(self):
        result = gpx_bytes_to_geojson(gpx(recorded_hike(60_000)))

        self.assertLessEqual(len(coordinates(result)), MAX_TRACK_POINTS)

    def test_a_reduced_track_keeps_its_start_end_and_shape(self):
        points = recorded_hike(60_000)
        line = gpx_bytes_to_geojson(gpx(points))['features'][0]['geometry']['coordinates']

        self.assertEqual(tuple(line[0]), (round(points[0][0], 6), round(points[0][1], 6)))
        self.assertEqual(tuple(line[-1]), (round(points[-1][0], 6), round(points[-1][1], 6)))
        # The sine wave's peaks survive: the track still reaches its full north-south extent.
        lats = [lat for _, lat in line]
        self.assertAlmostEqual(max(lats) - min(lats), 0.004, delta=0.0002)

    def test_a_short_track_keeps_every_corner(self):
        corners = [(1.0, 1.0), (1.01, 1.0), (1.01, 1.01), (1.0, 1.01)]

        line = gpx_bytes_to_geojson(gpx(corners))['features'][0]['geometry']['coordinates']

        self.assertEqual([tuple(c) for c in line], corners)

    def test_coordinates_are_rounded_to_about_ten_centimetres(self):
        line = gpx_bytes_to_geojson(gpx([(2.123456789, 41.987654321), (2.2, 41.9)]))[
            'features'][0]['geometry']['coordinates']

        self.assertEqual(tuple(line[0]), (2.123457, 41.987654))

    def test_each_segment_stays_its_own_line_with_its_track_name(self):
        result = gpx_bytes_to_geojson(gpx(recorded_hike(20_000), name='Day 1'))

        self.assertEqual(len(result['features']), 1)
        self.assertEqual(result['features'][0]['properties']['name'], 'Day 1')
        self.assertEqual(result['features'][0]['geometry']['type'], 'LineString')


class CollectionGpxPayloadTests(TestCase):
    def setUp(self):
        cache.clear()
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root)
        override.enable()
        self.addCleanup(override.disable)
        self.user = make_user('gpx-payload')
        self.client.force_login(self.user)

    def test_a_collection_with_a_large_transport_track_sends_it_at_map_resolution(self):
        trip = Collection.objects.create(user=self.user, name='Long walk')
        walk = Transportation.objects.create(user=self.user, collection=trip, type='walking', name='Camino')
        ContentAttachment.objects.create(
            user=self.user, content_object=walk, name='camino',
            file=ContentFile(gpx(recorded_hike(60_000)), name='camino.gpx'),
        )

        response = self.client.get(f'/api/collections/{trip.id}/')

        self.assertEqual(response.status_code, 200, response.content[:500])
        [transport] = response.json()['transportations']
        [attachment] = transport['attachments']
        self.assertLessEqual(len(coordinates(attachment['geojson'])), MAX_TRACK_POINTS)
