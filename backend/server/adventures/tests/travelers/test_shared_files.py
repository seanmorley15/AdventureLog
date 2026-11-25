"""
A traveler's copy shares the original's stored files instead of copying their bytes. Each file
stays until the last row that uses it is deleted, whichever side goes first.
"""

import shutil
import tempfile
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models.fields.files import FieldFile
from django.test import override_settings

from adventures.models import Activity, ContentAttachment, ContentImage, Location, Visit
from adventures.tests.base import AudienceTestBase
from adventures.tests.factories import GPX, PNG
from jobs.testing import discard_pending_jobs, run_pending_jobs
from users.services.account_deletion import delete_user_account

IMMICH_ID = '0b8e1c5e-55c1-4a5f-9a43-6f4f2d1f0a11'


def _past(day=1):
    return datetime(2026, 6, day, 10, 0, tzinfo=dt_timezone.utc)


def _rows(photos):
    """``(stored name, immich id)`` per photo, None for whichever it lacks."""
    return [(photo.image.name or None, photo.immich_id) for photo in photos]


def _cleanup():
    run_pending_jobs('adventures.delete_stored_file')


class SharedFilesBase(AudienceTestBase):
    def setUp(self):
        super().setUp()
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root)
        override.enable()
        self.addCleanup(override.disable)

    def _photo(self, user, target, name='photo.png'):
        return ContentImage.objects.create(user=user, image=ContentFile(PNG, name=name), content_object=target)

    def _immich(self, user, target):
        return ContentImage.objects.create(user=user, immich_id=IMMICH_ID, source='immich', content_object=target)


class TravelerCopiesShareFilesTests(SharedFilesBase):
    """Every way a traveler is given their own copy shares the files, and none of them reads one."""

    def setUp(self):
        super().setUp()
        self.hut_photo = self._photo(self.owner, self.hut, name='hut.png')
        self._immich(self.owner, self.hut)  # resolves through the owner's Immich: not for anyone else
        self.alone = Visit.objects.create(location=self.hut, start_date=_past())
        self.alone.travelers.set([self.editor])
        self.photo = self._photo(self.editor, self.alone)
        self.my_immich = self._immich(self.editor, self.alone)  # the editor's own: kept
        self.attachment = ContentAttachment.objects.create(
            user=self.editor, file=ContentFile(b'permit 42', name='permit.txt'), name='permit',
            content_object=self.alone,
        )
        self.run = Activity.objects.create(
            user=self.editor, visit=self.alone, name='Ridge hike', sport_type='Hike',
            gpx_file=ContentFile(GPX, name='ridge.gpx'),
        )
        self.run_photo = self._photo(self.editor, self.run, name='summit.png')
        self.names = {
            'hut': self.hut_photo.image.name,
            'photo': self.photo.image.name,
            'attachment': self.attachment.file.name,
            'gpx': self.run.gpx_file.name,
            'run_photo': self.run_photo.image.name,
        }
        discard_pending_jobs()

    def _release(self, act):
        with patch.object(FieldFile, 'open', side_effect=AssertionError('a copy must not read a file')):
            act()

    def _copy(self):
        return Location.objects.get(user=self.editor, name='Hut')

    def _assert_copy_shares_files(self):
        copy = self._copy()
        self.assertEqual([p.image.name for p in copy.images.all()], [self.names['hut']])
        visit = copy.visits.get()
        self.assertEqual(
            sorted(_rows(visit.images.all()), key=str), sorted([(self.names['photo'], None), (None, IMMICH_ID)], key=str)
        )
        [attachment] = visit.attachments.all()
        self.assertEqual((attachment.file.name, attachment.name, attachment.user), (self.names['attachment'], 'permit', self.editor))
        [run] = visit.activities.all()
        self.assertEqual((run.gpx_file.name, run.user), (self.names['gpx'], self.editor))
        self.assertEqual([p.image.name for p in run.images.all()], [self.names['run_photo']])
        _cleanup()
        for name in self.names.values():
            self.assertTrue(default_storage.exists(name), name)
        return copy

    def _assert_refcounted(self, copy):
        """The original going keeps the copy's files; the copy going last removes them."""
        Location.objects.filter(pk=self.hut.pk).delete()
        _cleanup()
        for name in self.names.values():
            self.assertTrue(default_storage.exists(name), name)
        copy.delete()
        _cleanup()
        for name in self.names.values():
            self.assertFalse(default_storage.exists(name), name)

    def test_leave_with_copies(self):
        self.as_user(self.editor)
        self._release(lambda: self.assertEqual(
            self.client.post(f'/api/collections/{self.trip.id}/leave/', {}, format='json').status_code, 204
        ))
        self.assertFalse(Visit.objects.filter(pk=self.alone.pk).exists())
        self._assert_refcounted(self._assert_copy_shares_files())

    def test_deleting_the_copy_keeps_the_originals_file(self):
        self.as_user(self.editor)
        self._release(lambda: self.client.post(f'/api/collections/{self.trip.id}/leave/', {}, format='json'))
        self._copy().delete()
        _cleanup()
        self.assertTrue(default_storage.exists(self.names['hut']))
        self.hut.delete()
        _cleanup()
        self.assertFalse(default_storage.exists(self.names['hut']))

    def test_owner_removes_member(self):
        self.as_user(self.owner)
        self._release(lambda: self.assertEqual(
            self.client.delete(f'/api/collections/{self.trip.id}/members/{self.editor.uuid}/').status_code, 204
        ))
        self._assert_refcounted(self._assert_copy_shares_files())

    def test_unlink(self):
        self.as_user(self.owner)
        self._release(lambda: self.assertEqual(
            self.client.delete(f'/api/locations/{self.hut.id}/collections/{self.trip.id}/').status_code, 200
        ))
        self._assert_refcounted(self._assert_copy_shares_files())

    def test_collection_delete(self):
        self.as_user(self.owner)
        self._release(lambda: self.assertEqual(self.client.delete(f'/api/collections/{self.trip.id}/').status_code, 204))
        self._assert_refcounted(self._assert_copy_shares_files())

    def test_account_deletion(self):
        self._release(lambda: delete_user_account(self.owner))
        self.assertFalse(Location.objects.filter(pk=self.hut.pk).exists())
        copy = self._assert_copy_shares_files()
        copy.delete()
        _cleanup()
        for name in self.names.values():
            self.assertFalse(default_storage.exists(name), name)

    def test_going_private(self):
        self.as_user(self.editor)
        self._release(lambda: self.assertEqual(
            self.client.patch('/api/account/', {'profile_visibility': 'private'}, format='json').status_code, 200
        ))
        self._assert_refcounted(self._assert_copy_shares_files())

    def test_duplicate_taking_my_visits(self):
        self.as_user(self.editor)
        self._release(lambda: self.assertEqual(self.client.post(
            f'/api/locations/{self.hut.id}/duplicate/', {'take_my_visits': True}, format='json'
        ).status_code, 201))
        self._assert_refcounted(self._assert_copy_shares_files())


class DuplicateIntegrationPhotosTests(SharedFilesBase):
    """A copy for someone else leaves out what only the original owner's Immich can show."""

    def setUp(self):
        super().setUp()
        self.hut_photo = self._photo(self.owner, self.hut, name='hut.png')
        self._immich(self.owner, self.hut)
        self.hut.is_public = True
        self.hut.save()

    def _duplicate(self, user):
        self.as_user(user)
        response = self.client.post(f'/api/locations/{self.hut.id}/duplicate/', {}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return Location.objects.get(pk=response.json()['id'])

    def test_someone_elses_copy_drops_immich_photos_and_shares_stored_ones(self):
        copy = self._duplicate(self.stranger)
        self.assertEqual(_rows(copy.images.all()), [(self.hut_photo.image.name, None)])
        self.assertEqual({p.user for p in copy.images.all()}, {self.stranger})

    def test_my_own_copy_keeps_everything(self):
        copy = self._duplicate(self.owner)
        self.assertEqual(
            sorted(_rows(copy.images.all()), key=str),
            sorted([(self.hut_photo.image.name, None), (None, IMMICH_ID)], key=str),
        )


class CopyKeepsACoverTests(SharedFilesBase):
    """Someone else's copy leaves out the owner's Immich photos; when one was the cover, the copy still gets one."""

    def _copy_for(self, user):
        from adventures.services.locations.copy import copy_location

        return copy_location(self.hut, user)

    def test_the_first_photo_copied_becomes_the_cover_when_the_immich_cover_is_left_out(self):
        ContentImage.objects.create(
            user=self.owner, immich_id=IMMICH_ID, source='immich', content_object=self.hut, is_primary=True,
        )
        names = {self._photo(self.owner, self.hut, name=n).image.name for n in ('a.png', 'b.png')}
        copy = self._copy_for(self.editor)
        covers = [p.image.name for p in copy.images.filter(is_primary=True)]
        # Photos have no order of their own; one of the copied ones, and only one, is the cover.
        self.assertEqual(len(covers), 1)
        self.assertIn(covers[0], names)
        self.assertEqual(copy.images.count(), 2)

    def test_a_copied_cover_stays_the_only_cover(self):
        self._photo(self.owner, self.hut, name='a.png')
        cover = self._photo(self.owner, self.hut, name='b.png')
        ContentImage.objects.filter(pk=cover.pk).update(is_primary=True)
        copy = self._copy_for(self.editor)
        self.assertEqual([p.image.name for p in copy.images.filter(is_primary=True)], [cover.image.name])

    def test_no_cover_is_made_up_when_the_original_had_none(self):
        self._photo(self.owner, self.hut, name='a.png')
        copy = self._copy_for(self.editor)
        self.assertFalse(copy.images.filter(is_primary=True).exists())

    def test_the_owner_keeps_their_immich_cover(self):
        ContentImage.objects.create(
            user=self.owner, immich_id=IMMICH_ID, source='immich', content_object=self.hut, is_primary=True,
        )
        self._photo(self.owner, self.hut, name='a.png')
        copy = self._copy_for(self.owner)
        self.assertEqual([p.immich_id for p in copy.images.filter(is_primary=True)], [IMMICH_ID])
