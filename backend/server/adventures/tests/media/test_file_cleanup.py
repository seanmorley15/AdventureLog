import io
import shutil
import tempfile
from datetime import date

from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models.signals import post_delete
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.db import connection
from PIL import Image

from adventures.models import (
    Activity,
    Category,
    Collection,
    CollectionItineraryItem,
    ContentAttachment,
    ContentImage,
    Location,
    Lodging,
    Visit,
)
from jobs.testing import queued_jobs, run_pending_jobs
from users.models import CustomUser


class RunsQueuedCleanup:
    """A delete queues the removal of its files; a worker runs it once the delete has committed."""

    def after_delete_the_worker_runs(self):
        return _AfterDelete()


class _AfterDelete:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            run_pending_jobs('adventures.delete_stored_file')


def png_file(name='photo.png'):
    buffer = io.BytesIO()
    Image.new('RGB', (4, 4), 'red').save(buffer, format='PNG')
    return ContentFile(buffer.getvalue(), name=name)


class StoredFileCleanupTests(RunsQueuedCleanup, TestCase):
    def setUp(self):
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root)
        override.enable()
        self.addCleanup(override.disable)

        self.user = CustomUser.objects.create_user(
            username='cleanup-user', email='cleanup-user@example.com', password='testpassword123'
        )
        self.location = Location.objects.create(user=self.user, name='Place')
        self.location_ct = ContentType.objects.get_for_model(Location)

    def add_image(self, parent=None, name='photo.png'):
        parent = parent or self.location
        return ContentImage.objects.create(
            user=self.user,
            content_type=ContentType.objects.get_for_model(type(parent)),
            object_id=parent.id,
            image=png_file(name),
        )

    def add_attachment(self, parent=None):
        parent = parent or self.location
        attachment = ContentAttachment(
            user=self.user,
            content_type=ContentType.objects.get_for_model(type(parent)),
            object_id=parent.id,
            name='notes',
        )
        attachment.file.save('notes.txt', ContentFile(b'hello'), save=True)
        return attachment

    def test_deleting_a_place_removes_its_photo_and_attachment_files_when_the_worker_runs(self):
        image_name = self.add_image().image.name
        attachment_name = self.add_attachment().file.name
        self.assertTrue(default_storage.exists(image_name))

        self.location.delete()
        # Nothing is removed from disk until the worker runs the clean-up the delete queued.
        self.assertTrue(default_storage.exists(image_name))
        run_pending_jobs('adventures.delete_stored_file')

        self.assertFalse(default_storage.exists(image_name))
        self.assertFalse(default_storage.exists(attachment_name))
        self.assertFalse(ContentImage.objects.exists())

    def test_files_stay_when_the_delete_is_rolled_back(self):
        image_name = self.add_image().image.name
        location_id = self.location.pk

        with self.after_delete_the_worker_runs():
            try:
                with transaction.atomic():
                    self.location.delete()
                    raise RuntimeError('roll back')
            except RuntimeError:
                pass
        self.assertEqual(queued_jobs('adventures.delete_stored_file').count(), 0)

        self.assertTrue(default_storage.exists(image_name))
        self.assertTrue(Location.objects.filter(pk=location_id).exists())

    def test_a_file_shared_by_two_photos_stays_until_the_last_one_is_deleted(self):
        first = self.add_image()
        other = Location.objects.create(user=self.user, name='Copy')
        second = ContentImage.objects.create(
            user=self.user, content_type=self.location_ct, object_id=other.id, image=first.image.name
        )
        shared_name = first.image.name

        with self.after_delete_the_worker_runs():
            first.delete()
        self.assertTrue(default_storage.exists(shared_name))

        with self.after_delete_the_worker_runs():
            second.delete()
        self.assertFalse(default_storage.exists(shared_name))

    def test_deleting_the_owner_removes_their_files(self):
        image_name = self.add_image().image.name
        attachment_name = self.add_attachment().file.name

        with self.after_delete_the_worker_runs():
            self.user.delete()

        self.assertFalse(default_storage.exists(image_name))
        self.assertFalse(default_storage.exists(attachment_name))

    def test_deleting_a_visit_removes_the_files_attached_to_it(self):
        visit = Visit.objects.create(location=self.location, start_date=None)
        image_name = self.add_image(visit).image.name

        with self.after_delete_the_worker_runs():
            visit.delete()

        self.assertFalse(default_storage.exists(image_name))

    def test_deleting_a_lodging_removes_its_files(self):
        lodging = Lodging.objects.create(user=self.user, name='Hut')
        image_name = self.add_image(lodging).image.name
        attachment_name = self.add_attachment(lodging).file.name

        with self.after_delete_the_worker_runs():
            lodging.delete()

        self.assertFalse(default_storage.exists(image_name))
        self.assertFalse(default_storage.exists(attachment_name))

    def test_deleting_an_activity_removes_its_gpx_file(self):
        trip = Collection.objects.create(user=self.user, name='Walks')
        activity = Activity(user=self.user, collection=trip, name='Walk')
        activity.gpx_file.save('walk.gpx', ContentFile(b'<gpx/>'), save=True)
        name = activity.gpx_file.name
        self.assertTrue(default_storage.exists(name))

        with self.after_delete_the_worker_runs():
            Activity.objects.filter(pk=activity.pk).delete()

        self.assertFalse(default_storage.exists(name))

    def test_deleting_a_collection_removes_day_files(self):
        trip = Collection.objects.create(
            user=self.user, name='Trip', type='trip', start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
        )
        from adventures.services.day_plan import convert_collection

        convert_collection(trip)
        day = trip.itinerary_days.get(index=1)
        activity = Activity(user=self.user, day=day, name='Day walk')
        activity.gpx_file.save('day.gpx', ContentFile(b'<gpx/>'), save=True)
        photo = ContentImage.objects.create(
            user=self.user,
            content_type=ContentType.objects.get_for_model(type(day)),
            object_id=day.id,
            image=png_file('day.png'),
        )
        names = [activity.gpx_file.name, photo.image.name]

        with self.after_delete_the_worker_runs():
            trip.delete()

        for name in names:
            self.assertFalse(default_storage.exists(name), name)
        self.assertFalse(Activity.objects.filter(pk=activity.pk).exists())


class ItineraryItemCleanupTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='items-user', email='items-user@example.com', password='testpassword123'
        )
        self.trip = Collection.objects.create(user=self.user, name='Trip')
        self.location = Location.objects.create(user=self.user, name='Place')

    def place(self, obj):
        return CollectionItineraryItem.objects.create(
            collection=self.trip,
            content_type=ContentType.objects.get_for_model(type(obj)),
            object_id=obj.id,
            is_global=True,
            order=CollectionItineraryItem.objects.count(),
        )

    def test_deleting_a_place_removes_its_itinerary_items(self):
        kept = Location.objects.create(user=self.user, name='Other')
        self.place(self.location)
        self.place(kept)

        self.location.delete()

        self.assertEqual(
            list(CollectionItineraryItem.objects.values_list('object_id', flat=True)), [kept.id]
        )

    def test_deleting_a_lodging_or_visit_removes_its_itinerary_items(self):
        lodging = Lodging.objects.create(user=self.user, name='Hut')
        visit = Visit.objects.create(location=self.location)
        self.place(lodging)
        self.place(visit)

        lodging.delete()
        visit.delete()

        self.assertFalse(CollectionItineraryItem.objects.exists())

    def test_deleting_unrelated_models_does_not_touch_the_itinerary_table(self):
        category = Category.objects.create(user=self.user, name='quiet', display_name='Quiet', icon='x')

        with CaptureQueriesContext(connection) as queries:
            category.delete()

        self.assertFalse(any('collectionitineraryitem' in q['sql'].lower() for q in queries.captured_queries))

    def test_the_signal_is_connected_only_to_the_models_an_item_can_point_at(self):
        senders = {
            getattr(receiver[1](), '__name__', None)
            for receiver in post_delete.receivers
        }
        # No receiver is registered for every model any more.
        from adventures import signals

        unscoped = [
            r for r in post_delete.receivers
            if r[0][1] is None and getattr(r[1](), '__module__', '') == signals.__name__
        ]
        self.assertEqual(unscoped, [])


class SharedTrackCleanupTests(TestCase):
    """
    Rows can share one stored file (a copy keeps the original's name). Deleting a row never
    removes the file directly: the refcounted clean-up job does, once no row uses it.
    """

    def setUp(self):
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root)
        override.enable()
        self.addCleanup(override.disable)

        self.owner = CustomUser.objects.create_user(
            username='track-owner', email='track-owner@example.com', password='testpassword123'
        )
        self.other = CustomUser.objects.create_user(
            username='track-other', email='track-other@example.com', password='testpassword123'
        )
        self.activity = self.add_activity(self.owner)
        self.name = self.activity.gpx_file.name
        # The other user's copy points at the same stored file.
        self.copy = self.add_activity(self.other, name=self.name)

    def add_activity(self, user, name=None):
        visit = Visit.objects.create(location=Location.objects.create(user=user, name='Ridge'))
        activity = Activity(user=user, visit=visit, name='Walk')
        if name is None:
            activity.gpx_file.save('walk.gpx', ContentFile(b'<gpx/>'), save=True)
        else:
            activity.gpx_file = name
            activity.save()
        return activity

    def test_destroying_an_activity_keeps_a_track_another_activity_uses(self):
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(self.owner)
        response = client.delete(f'/api/activities/{self.activity.pk}/')
        self.assertEqual(response.status_code, 204, response.content)
        self.assertTrue(default_storage.exists(self.name))
        run_pending_jobs('adventures.delete_stored_file')
        self.assertTrue(default_storage.exists(self.name))

        client.force_authenticate(self.other)
        response = client.delete(f'/api/activities/{self.copy.pk}/')
        self.assertEqual(response.status_code, 204, response.content)
        run_pending_jobs('adventures.delete_stored_file')
        self.assertFalse(default_storage.exists(self.name))

    def test_account_deletion_keeps_a_track_another_user_uses(self):
        from users.services.account_deletion import delete_user_account

        delete_user_account(self.owner)
        self.assertTrue(default_storage.exists(self.name))
        run_pending_jobs('adventures.delete_stored_file')
        self.assertTrue(default_storage.exists(self.name))
        self.assertTrue(Activity.objects.filter(pk=self.copy.pk).exists())

    def test_rolled_back_account_data_clearing_keeps_the_track(self):
        from adventures.services.account_data import clear_user_adventure_data

        self.copy.delete()  # the owner's row is the only one left
        run_pending_jobs('adventures.delete_stored_file')
        try:
            with transaction.atomic():
                clear_user_adventure_data(self.owner)
                raise RuntimeError('roll back')
        except RuntimeError:
            pass
        run_pending_jobs('adventures.delete_stored_file')
        self.assertTrue(default_storage.exists(self.name))
        self.assertTrue(Activity.objects.filter(pk=self.activity.pk).exists())


class ReplacedAttachmentCleanupTests(TestCase):
    """A new file on an attachment queues the old one's removal, once the change commits."""

    setUp = StoredFileCleanupTests.setUp
    add_attachment = StoredFileCleanupTests.add_attachment

    def _replace(self, attachment):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=self.user)
        with self.captureOnCommitCallbacks(execute=True):
            response = client.patch(
                f'/api/attachments/{attachment.id}/',
                {'file': SimpleUploadedFile('new.txt', b'new contents')},
                format='multipart',
            )
        self.assertEqual(response.status_code, 200, response.content)
        attachment.refresh_from_db()
        return attachment.file.name

    def test_the_old_file_goes_when_the_worker_runs(self):
        attachment = self.add_attachment()
        old_name = attachment.file.name
        new_name = self._replace(attachment)
        self.assertNotEqual(new_name, old_name)
        run_pending_jobs('adventures.delete_stored_file')
        self.assertFalse(default_storage.exists(old_name))
        self.assertTrue(default_storage.exists(new_name))

    def test_an_old_file_another_row_shares_stays(self):
        attachment = self.add_attachment()
        old_name = attachment.file.name
        ContentAttachment.objects.create(
            user=self.user, content_type=self.location_ct, object_id=self.location.id, name='copy', file=old_name,
        )
        self._replace(attachment)
        run_pending_jobs('adventures.delete_stored_file')
        self.assertTrue(default_storage.exists(old_name))

    def test_renaming_without_a_file_queues_nothing(self):
        from rest_framework.test import APIClient

        attachment = self.add_attachment()
        client = APIClient()
        client.force_authenticate(user=self.user)
        with self.captureOnCommitCallbacks(execute=True):
            client.patch(f'/api/attachments/{attachment.id}/', {'name': 'renamed'}, format='json')
        self.assertFalse(queued_jobs('adventures.delete_stored_file').exists())
