from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from adventures.models import Activity, Location, Visit

User = get_user_model()


@override_settings(DEBUG=True)
class ProtectedMediaTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='media-owner',
            email='media-owner@example.com',
            password='testpassword123',
        )
        self.other = User.objects.create_user(
            username='media-other',
            email='media-other@example.com',
            password='testpassword123',
        )
        self.location = Location.objects.create(
            user=self.owner,
            name='Private Trailhead',
            is_public=False,
        )
        self.visit = Visit.objects.create(location=self.location)
        self.gpx_name = 'test-track.gpx'
        self.gpx_path = f'activities/{self.gpx_name}'
        self._write_media_file(self.gpx_path, b'SECRET_GPX_TRACK_DATA')
        self.activity = Activity.objects.create(
            user=self.owner,
            visit=self.visit,
            name='Morning Run',
            gpx_file=self.gpx_path,
        )

    def _write_media_file(self, relative_path, content):
        absolute_path = Path(settings.MEDIA_ROOT) / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_path.write_bytes(content)

    def test_anonymous_user_cannot_download_private_gpx(self):
        response = self.client.get(f'/media/{self.gpx_path}')
        self.assertEqual(response.status_code, 403)

    def test_unauthorized_user_cannot_download_private_gpx(self):
        self.client.force_login(self.other)
        response = self.client.get(f'/media/{self.gpx_path}')
        self.assertEqual(response.status_code, 403)

    def test_owner_can_download_private_gpx(self):
        self.client.force_login(self.owner)
        response = self.client.get(f'/media/{self.gpx_path}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'SECRET_GPX_TRACK_DATA')

    def test_unknown_media_subtree_is_denied(self):
        self._write_media_file('secret-stash/leak.txt', b'leaked')
        response = self.client.get('/media/secret-stash/leak.txt')
        self.assertEqual(response.status_code, 403)

    def test_public_media_subtree_is_accessible_without_auth(self):
        self._write_media_file('flags/us.png', b'flag-bytes')
        response = self.client.get('/media/flags/us.png')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'flag-bytes')

    def test_path_traversal_cannot_bypass_gpx_protection(self):
        response = self.client.get(f'/media/profile-pics/../{self.gpx_path}')
        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_can_download_public_location_gpx(self):
        public_location = Location.objects.create(
            user=self.owner,
            name='Public Trail',
            is_public=True,
        )
        public_visit = Visit.objects.create(location=public_location)
        public_gpx_path = 'activities/public-track.gpx'
        self._write_media_file(public_gpx_path, b'PUBLIC_GPX_DATA')
        Activity.objects.create(
            user=self.owner,
            visit=public_visit,
            name='Public Run',
            gpx_file=public_gpx_path,
        )

        response = self.client.get(f'/media/{public_gpx_path}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'PUBLIC_GPX_DATA')
