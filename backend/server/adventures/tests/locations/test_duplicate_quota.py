"""
Copying a place you chose to copy counts against your media storage limit; copies you are given
when you lose access to a place never do.
"""

import shutil
import tempfile
from datetime import datetime, timezone as dt_timezone

from django.core.files.base import ContentFile
from django.test import override_settings

from adventures.models import ContentImage, Location, Visit
from adventures.services.media_quota import incoming_bytes_for_names
from adventures.tests.base import AudienceTestBase
from adventures.tests.factories import PNG


class QuotaTestBase(AudienceTestBase):
    def setUp(self):
        super().setUp()
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root)
        override.enable()
        self.addCleanup(override.disable)

        self.photo = ContentImage.objects.create(
            user=self.owner, image=ContentFile(PNG, name='hut.png'), content_object=self.hut
        )
        self.size = self.photo.image.size
        self.hut.is_public = True
        self.hut.save()

    def _duplicate(self, user, **body):
        self.as_user(user)
        return self.client.post(f'/api/locations/{self.hut.id}/duplicate/', body, format='json')

    def _rows(self):
        return Location.objects.count(), ContentImage.objects.count()


class DuplicateQuotaTests(QuotaTestBase):
    def test_a_copy_over_the_limit_is_a_413_and_creates_nothing(self):
        before = self._rows()
        with override_settings(MEDIA_STORAGE_LIMIT_BYTES=self.size - 1):
            response = self._duplicate(self.stranger)
        self.assertEqual(response.status_code, 413, response.content)
        self.assertEqual(response.json()['code'], 'media_quota_exceeded')
        self.assertEqual(self._rows(), before)

    def test_a_copy_within_the_limit_is_made(self):
        with override_settings(MEDIA_STORAGE_LIMIT_BYTES=self.size):
            self.assertEqual(self._duplicate(self.stranger).status_code, 201)

    def test_a_file_already_yours_counts_once(self):
        with override_settings(MEDIA_STORAGE_LIMIT_BYTES=self.size):
            self.assertEqual(self._duplicate(self.stranger).status_code, 201)
            # The second copy shares the same file, which already counts for them.
            self.assertEqual(self._duplicate(self.stranger).status_code, 201)
        self.assertEqual(incoming_bytes_for_names(self.stranger, [self.photo.image.name]), 0)

    def test_copying_your_own_place_adds_nothing_even_over_the_limit(self):
        with override_settings(MEDIA_STORAGE_LIMIT_BYTES=1):
            self.assertEqual(self._duplicate(self.owner).status_code, 201)

    def test_incoming_bytes_count_each_new_name_once_and_skip_missing_files(self):
        names = [self.photo.image.name, self.photo.image.name, 'images/missing.webp', '']
        self.assertEqual(incoming_bytes_for_names(self.stranger, names), self.size)
        self.assertEqual(incoming_bytes_for_names(self.owner, names), 0)


class ReleaseIgnoresQuotaTests(QuotaTestBase):
    """Copies a traveler is given (or takes before leaving) are never refused for storage."""

    def setUp(self):
        super().setUp()
        self.visit = Visit.objects.create(location=self.hut, start_date=datetime(2026, 6, 1, tzinfo=dt_timezone.utc))
        self.visit.travelers.set([self.owner, self.editor])

    def test_taking_my_visits_is_not_refused(self):
        with override_settings(MEDIA_STORAGE_LIMIT_BYTES=1):
            response = self._duplicate(self.editor, take_my_visits=True)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Location.objects.get(pk=response.json()['id']).images.count(), 1)

    def test_leaving_with_copies_is_not_refused(self):
        self.as_user(self.editor)
        with override_settings(MEDIA_STORAGE_LIMIT_BYTES=1):
            response = self.client.post(f'/api/collections/{self.trip.id}/leave/', {}, format='json')
        self.assertEqual(response.status_code, 204, response.content)
        self.assertEqual(Location.objects.get(user=self.editor, name='Hut').images.count(), 1)

    def test_removal_is_not_refused(self):
        self.as_user(self.owner)
        with override_settings(MEDIA_STORAGE_LIMIT_BYTES=1):
            response = self.client.delete(f'/api/collections/{self.trip.id}/members/{self.editor.uuid}/')
        self.assertEqual(response.status_code, 204, response.content)
        self.assertEqual(Location.objects.get(user=self.editor, name='Hut').images.count(), 1)
