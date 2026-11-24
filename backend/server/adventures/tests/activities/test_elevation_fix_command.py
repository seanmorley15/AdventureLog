"""The elevation fix command measures stored tracks and leaves imported totals alone."""

import shutil
import tempfile
from io import StringIO

from django.core.files.base import ContentFile
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from adventures.models import Activity, Location, Visit
from adventures.tests.activities.factories import hill, make_gpx, walk
from core.testing import make_user


class ElevationFixCommandTests(TestCase):
    def setUp(self):
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root)
        override.enable()
        self.addCleanup(override.disable)

        user = make_user('fixer')
        self.visit = Visit.objects.create(location=Location.objects.create(user=user, name='Peak'))
        self.user = user

    def activity(self, data=None, **fields):
        data = data if data is not None else make_gpx(walk(601, ele=hill))
        activity = Activity(user=self.user, visit=self.visit, name='Climb', **fields)
        activity.gpx_file.save('track.gpx', ContentFile(data), save=False)
        activity.save()
        return activity

    def run_command(self, *args):
        out = StringIO()
        call_command('activity_elevation_fix', *args, stdout=out)
        return out.getvalue()

    def test_it_replaces_a_naive_figure_with_the_measured_one(self):
        activity = self.activity(elevation_gain=900.0)
        self.run_command()
        activity.refresh_from_db()
        self.assertAlmostEqual(activity.elevation_gain, 100.0, delta=5)

    def test_a_dry_run_saves_nothing(self):
        activity = self.activity(elevation_gain=900.0)
        self.assertIn('Would update 1', self.run_command('--dry-run'))
        activity.refresh_from_db()
        self.assertEqual(activity.elevation_gain, 900.0)

    def test_imported_activities_are_skipped_without_force(self):
        activity = self.activity(elevation_gain=900.0, external_service_id='123')
        self.run_command()
        activity.refresh_from_db()
        self.assertEqual(activity.elevation_gain, 900.0)
        self.run_command('--force')
        activity.refresh_from_db()
        self.assertAlmostEqual(activity.elevation_gain, 100.0, delta=5)

    def test_a_track_without_altitude_is_never_zeroed(self):
        activity = self.activity(make_gpx(walk(100, ele=lambda i: None)), elevation_gain=50.0)
        self.run_command()
        activity.refresh_from_db()
        self.assertEqual(activity.elevation_gain, 50.0)

    def test_it_can_target_one_activity_by_uuid(self):
        target, other = self.activity(elevation_gain=900.0), self.activity(elevation_gain=900.0)
        self.run_command('--activity-id', str(target.id))
        target.refresh_from_db(), other.refresh_from_db()
        self.assertAlmostEqual(target.elevation_gain, 100.0, delta=5)
        self.assertEqual(other.elevation_gain, 900.0)

    def test_an_unknown_activity_is_an_error(self):
        with self.assertRaises(CommandError):
            self.run_command('--activity-id', '00000000-0000-0000-0000-000000000000')
