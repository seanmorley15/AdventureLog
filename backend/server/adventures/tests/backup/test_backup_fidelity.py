"""Things a backup used to lose or mix up, each pinned on its own."""

import io
import json
import shutil
import tempfile
import zipfile
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from adventures.models import (
    Activity, Collection, CollectionComment, ContentImage, Location, Transportation, Trail,
)
from adventures.tests.factories import build_rich_account
from users.models import CustomUser


class BackupFidelityTests(APITestCase):
    def setUp(self):
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root)
        override.enable()
        self.addCleanup(override.disable)
        self.owner = CustomUser.objects.create_user(
            username='fid-owner', email='fid-owner@example.com', password='testpassword123'
        )
        self.client.force_authenticate(user=self.owner)

    def export_data(self):
        response = self.client.get('/api/backup/export/')
        self.assertEqual(response.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            return json.loads(archive.read('data.json')), response.content

    def restore(self, content):
        upload = SimpleUploadedFile('backup.zip', content, content_type='application/zip')
        response = self.client.post('/api/backup/import/', {'file': upload, 'confirm': 'yes'}, format='multipart')
        self.assertEqual(response.status_code, 200, response.content)

    def test_records_of_same_named_collections_stay_with_their_own_collection(self):
        first = Collection.objects.create(user=self.owner, name='Weekend')
        second = Collection.objects.create(user=self.owner, name='Weekend')
        Transportation.objects.create(user=self.owner, collection=first, type='car', name='Drive A')
        Transportation.objects.create(user=self.owner, collection=second, type='car', name='Drive B')

        data, content = self.export_data()
        refs = {t['name']: t['collection_export_id'] for t in data['transportation']}
        self.assertEqual(sorted(refs.values()), [0, 1])
        self.assertNotEqual(refs['Drive A'], refs['Drive B'])

        self.restore(content)
        drive_a = Transportation.objects.get(name='Drive A')
        drive_b = Transportation.objects.get(name='Drive B')
        self.assertNotEqual(drive_a.collection_id, drive_b.collection_id)

    def test_zero_values_are_kept_not_turned_into_missing(self):
        trip = Collection.objects.create(user=self.owner, name='Flat day')
        Activity.objects.create(
            user=self.owner, collection=trip, name='Stroll', distance=0.0, elevation_gain=0.0,
            calories=0.0, moving_time=timedelta(0),
        )

        data, content = self.export_data()
        exported = data['day_activities'][0]
        self.assertEqual(
            (exported['distance'], exported['elevation_gain'], exported['calories'], exported['moving_time']),
            (0.0, 0.0, 0.0, 0.0),
        )

    def test_everything_the_rich_account_has_survives_a_restore(self):
        friend = CustomUser.objects.create_user(
            username='fid-friend', email='fid-friend@example.com', password='testpassword123', public_profile=True
        )
        build_rich_account(self.owner, friend)
        _, content = self.export_data()

        self.restore(content)

        train = Transportation.objects.get(name='TGV to Annecy')
        self.assertEqual((train.start_code, train.end_code), ('PAR', 'NCY'))
        trail = Trail.objects.get(name='Tête Rousse route')
        self.assertEqual(ContentImage.objects.filter(object_id=trail.id).count(), 1)
        ascent = Activity.objects.get(name='Ascent')
        self.assertEqual(ContentImage.objects.filter(object_id=ascent.id).count(), 1)
        run = Activity.objects.get(name='Morning run')
        self.assertEqual((run.external_service_id, run.start_point is not None, run.end_point is not None),
                         ('strava-7', True, True))
        self.assertEqual((run.calories, run.moving_time), (0.0, timedelta(0)))
        comment = CollectionComment.objects.get(body='Book the hut early')
        self.assertIsNotNone(comment.placement)
        self.assertEqual(comment.placement.collection_id, comment.collection_id)
        self.assertEqual(Location.objects.get(pk=comment.placement.object_id).name, 'Refuge du Goûter')
