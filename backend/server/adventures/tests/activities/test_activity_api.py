"""Activities from a recorded file, through the API: analyze, create, replace and edit."""

import shutil
import tempfile
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from adventures.models import Activity, Collection, CollectionItineraryDay, Location, Visit
from adventures.tests.activities.factories import (
    hill, make_fit, make_gpx, make_kml, make_kmz, make_tcx, walk,
)
from users.models import CustomUser

SAMPLES = walk(601, speed=1.4, ele=hill, hr=lambda i: 140)

FORMATS = {
    'gpx': ('ride.gpx', make_gpx(SAMPLES)),
    'fit': ('ride.fit', make_fit(SAMPLES, ascent=120, calories=300)),
    'tcx': ('ride.tcx', make_tcx(SAMPLES)),
    'kml': ('ride.kml', make_kml(SAMPLES)),
    'kmz': ('ride.kmz', make_kmz(SAMPLES)),
}


def upload(name, data):
    return SimpleUploadedFile(name, data, content_type='application/octet-stream')


class ActivityFileTestCase(APITestCase):
    def setUp(self):
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root)
        override.enable()
        self.addCleanup(override.disable)

        self.owner = CustomUser.objects.create_user(
            username='activity-owner', email='activity-owner@example.com', password='testpassword123'
        )
        self.stranger = CustomUser.objects.create_user(
            username='activity-stranger', email='activity-stranger@example.com', password='testpassword123'
        )
        self.client.force_authenticate(user=self.owner)
        self.location = Location.objects.create(user=self.owner, name='Montserrat')
        self.visit = Visit.objects.create(
            location=self.location, start_date='2026-06-06T00:00:00Z', end_date='2026-06-06T00:00:00Z'
        )

    def create(self, name, data, **fields):
        body = {'name': 'Ride', 'visit': str(self.visit.id), 'gpx_file': upload(name, data), **fields}
        return self.client.post('/api/activities/', body, format='multipart')


class AnalyzeTests(ActivityFileTestCase):
    def analyze(self, name, data):
        return self.client.post('/api/activities/analyze/', {'file': upload(name, data)}, format='multipart')

    def test_every_format_is_analyzed(self):
        for kind, (name, data) in FORMATS.items():
            with self.subTest(kind=kind):
                response = self.analyze(name, data)
                self.assertEqual(response.status_code, 200, response.content)
                body = response.json()
                self.assertEqual(body['format'], kind if kind != 'kmz' else 'kml')
                self.assertEqual(body['point_count'], 601)
                self.assertAlmostEqual(body['values']['distance'], 840.0, delta=2)
                self.assertEqual(body['geojson']['features'][0]['geometry']['type'], 'LineString')

    def test_the_preview_track_carries_elevation(self):
        coordinates = self.analyze(*FORMATS['gpx']).json()['geojson']['features'][0]['geometry']['coordinates']
        self.assertEqual(len(coordinates[0]), 3)

    def test_it_reports_where_each_value_came_from(self):
        body = self.analyze(*FORMATS['fit']).json()
        self.assertEqual(body['values']['elevation_gain'], 120)
        self.assertEqual(body['sources']['elevation_gain'], 'device')
        self.assertEqual(body['sources']['elev_high'], 'computed')

    def test_nothing_is_saved(self):
        self.analyze(*FORMATS['gpx'])
        self.assertEqual(Activity.objects.count(), 0)

    def test_an_unreadable_file_is_a_400_with_a_code(self):
        response = self.analyze('notes.gpx', b'not a track')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'activity.unreadable_track')

    def test_it_needs_a_login(self):
        self.client.force_authenticate(user=None)
        response = self.analyze(*FORMATS['gpx'])
        self.assertIn(response.status_code, (401, 403))


class CreateTests(ActivityFileTestCase):
    def test_a_file_fills_every_field_the_request_left_out(self):
        response = self.create(*FORMATS['gpx'])
        self.assertEqual(response.status_code, 201, response.content)
        activity = Activity.objects.get(pk=response.json()['id'])
        self.assertAlmostEqual(activity.distance, 840.0, delta=2)
        self.assertAlmostEqual(activity.elevation_gain, 100.0, delta=5)
        self.assertEqual(activity.moving_time.total_seconds(), 600)
        self.assertEqual(activity.sport_type, 'Hike')
        self.assertEqual(activity.average_heart_rate, 140)
        self.assertIsNotNone(activity.start_date)
        self.assertIsNotNone(activity.start_point)

    def test_every_format_is_stored_as_gpx(self):
        for kind, (name, data) in FORMATS.items():
            with self.subTest(kind=kind):
                response = self.create(name, data)
                self.assertEqual(response.status_code, 201, response.content)
                stored = Activity.objects.get(pk=response.json()['id']).gpx_file
                self.assertTrue(stored.name.endswith('.gpx'), stored.name)
                self.assertIn(b'<gpx', Path(settings.MEDIA_ROOT, stored.name).read_bytes())
                self.assertTrue(response.json()['geojson']['features'])

    def test_what_the_request_sent_wins_over_the_file(self):
        response = self.create(*FORMATS['fit'], distance=5000, elevation_gain=7, sport_type='Ride')
        activity = Activity.objects.get(pk=response.json()['id'])
        self.assertEqual((activity.distance, activity.elevation_gain, activity.sport_type), (5000, 7, 'Ride'))
        self.assertEqual(activity.calories, 300)  # still filled from the file

    def test_device_totals_win_over_the_points(self):
        response = self.create(*FORMATS['fit'])
        self.assertEqual(Activity.objects.get(pk=response.json()['id']).elevation_gain, 120)

    def test_a_day_activity_is_filled_the_same_way(self):
        trip = Collection.objects.create(user=self.owner, name='Ridge', type='trip')
        day = CollectionItineraryDay.objects.create(collection=trip, index=1)
        response = self.client.post(
            '/api/activities/',
            {'name': 'Day hike', 'day': str(day.id), 'gpx_file': upload(*FORMATS['tcx'])},
            format='multipart',
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertAlmostEqual(response.json()['distance'], 840.0, delta=2)

    def test_an_ideas_activity_is_filled_the_same_way(self):
        trip = Collection.objects.create(user=self.owner, name='Someday', type='trip')
        response = self.client.post(
            '/api/activities/',
            {'name': 'Maybe', 'collection': str(trip.id), 'gpx_file': upload(*FORMATS['kml'])},
            format='multipart',
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertAlmostEqual(response.json()['distance'], 840.0, delta=2)

    def test_a_file_that_is_not_a_track_is_refused(self):
        response = self.create('track.gpx', b'<html>nope</html>')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'activity.unreadable_track')
        self.assertEqual(Activity.objects.count(), 0)

    def test_a_disallowed_extension_is_refused(self):
        response = self.create('track.pdf', FORMATS['gpx'][1])
        self.assertEqual(response.status_code, 400)

    def test_an_upload_over_the_media_limit_is_a_413(self):
        with override_settings(MEDIA_STORAGE_LIMIT_BYTES=200):
            response = self.create(*FORMATS['gpx'])
        self.assertEqual(response.status_code, 413, response.content)
        self.assertEqual(response.json()['code'], 'media_quota_exceeded')

    def test_a_stranger_cannot_attach_to_someone_elses_visit(self):
        self.client.force_authenticate(user=self.stranger)
        self.assertEqual(self.create(*FORMATS['gpx']).status_code, 403)


class UpdateTests(ActivityFileTestCase):
    def test_a_new_file_replaces_the_track_and_fills_missing_fields(self):
        first = self.create(*FORMATS['gpx']).json()['id']
        activity = Activity.objects.get(pk=first)
        old_name = activity.gpx_file.name
        with mock.patch('adventures.tasks.delete_stored_file.defer') as defer, \
                self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                f'/api/activities/{first}/',
                {'gpx_file': upload(*FORMATS['fit']), 'name': 'Renamed'},
                format='multipart',
            )
        self.assertEqual(response.status_code, 200, response.content)
        activity.refresh_from_db()
        self.assertEqual(activity.name, 'Renamed')
        self.assertNotEqual(activity.gpx_file.name, old_name)
        self.assertEqual(activity.calories, 300)
        defer.assert_called_once_with(model_label='adventures.Activity', field_name='gpx_file', name=old_name)

    def test_editing_without_a_file_changes_only_what_was_sent(self):
        created = self.create(*FORMATS['gpx']).json()
        response = self.client.patch(f'/api/activities/{created["id"]}/', {'name': 'Better name'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        activity = Activity.objects.get(pk=created['id'])
        self.assertEqual(activity.name, 'Better name')
        self.assertAlmostEqual(activity.distance, 840.0, delta=2)

    def test_a_bad_replacement_file_leaves_the_activity_alone(self):
        created = self.create(*FORMATS['gpx']).json()
        before = Activity.objects.get(pk=created['id']).gpx_file.name
        response = self.client.patch(
            f'/api/activities/{created["id"]}/', {'gpx_file': upload('x.gpx', b'junk')}, format='multipart'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Activity.objects.get(pk=created['id']).gpx_file.name, before)
