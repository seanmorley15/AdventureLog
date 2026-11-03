"""The full-backup file, pinned. A refactor of the exporter must not change a byte of its meaning."""

import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from adventures.models import Collection, ContentImage, Location
from adventures.tests.factories import build_rich_account
from adventures.tests.backup.normalize import assert_matches_golden, read_archive
from users.models import CustomUser
from worldtravel.models import VisitedCity, VisitedRegion


class FullBackupGoldenTests(APITestCase):
    def setUp(self):
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root, ADVENTURELOG_RELEASE_VERSION='test')
        override.enable()
        self.addCleanup(override.disable)

        self.owner = CustomUser.objects.create_user(
            username='bk-owner', email='bk-owner@example.com', password='testpassword123'
        )
        self.friend = CustomUser.objects.create_user(
            username='bk-friend', email='bk-friend@example.com', password='testpassword123', public_profile=True
        )
        self.objects = build_rich_account(self.owner, self.friend)
        self.client.force_authenticate(user=self.owner)

    def export(self):
        response = self.client.get('/api/backup/export/')
        self.assertEqual(response.status_code, 200)
        return response.content

    def read(self, content):
        return read_archive(content, users={self.owner.uuid: 'owner', self.friend.uuid: 'friend'})

    def restore(self, content):
        upload = SimpleUploadedFile('backup.zip', content, content_type='application/zip')
        return self.client.post('/api/backup/import/', {'file': upload, 'confirm': 'yes'}, format='multipart')

    def test_export_matches_the_golden_file(self):
        data, members = self.read(self.export())

        assert_matches_golden(self, 'backup_export.json', data)
        assert_matches_golden(self, 'backup_export_members.json', members)

    def test_restoring_an_export_and_exporting_again_gives_the_same_file(self):
        first, first_members = self.read(self.export())

        response = self.restore(self.export())
        self.assertEqual(response.status_code, 200, response.content)
        second, second_members = self.read(self.export())

        # By design a file cannot add members or write as another account: shared people come
        # back as pending invites, and a comment keeps its author's name but not their account.
        for collection in first['collections']:
            collection['members'] = []
            collection['shared_with_user_ids'] = []
            for comment in collection['comments']:
                if comment['author_user_uuid'] not in (None, '<user-owner>'):
                    comment['author_user_uuid'] = None

        self.assertEqual(second, first)
        self.assertEqual(second_members, first_members)

    def test_restore_summary_counts(self):
        response = self.restore(self.export())

        self.assertEqual(response.status_code, 200, response.content)
        summary = response.json()['summary']
        assert_matches_golden(self, 'backup_import_summary.json', summary)

    def test_restore_replaces_what_was_there_and_recreates_everything(self):
        stale = Location.objects.create(user=self.owner, name='Will be replaced')
        self.restore(self.export())

        self.assertFalse(Location.objects.filter(pk=stale.pk).exists())
        self.assertEqual(Collection.objects.filter(user=self.owner).count(), 2)
        self.assertEqual(VisitedRegion.objects.filter(user=self.owner).count(), 1)
        self.assertEqual(VisitedCity.objects.filter(user=self.owner).count(), 1)
        self.assertEqual(ContentImage.objects.filter(user=self.owner).count(), 12)
