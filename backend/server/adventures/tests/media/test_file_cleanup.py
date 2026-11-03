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
from users.models import CustomUser


def png_file(name='photo.png'):
    buffer = io.BytesIO()
    Image.new('RGB', (4, 4), 'red').save(buffer, format='PNG')
    return ContentFile(buffer.getvalue(), name=name)


class StoredFileCleanupTests(TestCase):
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

    def test_deleting_a_place_removes_its_photo_and_attachment_files_after_commit(self):
        image_name = self.add_image().image.name
        attachment_name = self.add_attachment().file.name
        self.assertTrue(default_storage.exists(image_name))

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            self.location.delete()
            # Nothing is removed from disk until the database delete has committed.
            self.assertTrue(default_storage.exists(image_name))
        for callback in callbacks:
            callback()

        self.assertFalse(default_storage.exists(image_name))
        self.assertFalse(default_storage.exists(attachment_name))
        self.assertFalse(ContentImage.objects.exists())

    def test_files_stay_when_the_delete_is_rolled_back(self):
        image_name = self.add_image().image.name
        location_id = self.location.pk

        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    self.location.delete()
                    raise RuntimeError('roll back')
            except RuntimeError:
                pass

        self.assertTrue(default_storage.exists(image_name))
        self.assertTrue(Location.objects.filter(pk=location_id).exists())

    def test_a_file_shared_by_two_photos_stays_until_the_last_one_is_deleted(self):
        first = self.add_image()
        other = Location.objects.create(user=self.user, name='Copy')
        second = ContentImage.objects.create(
            user=self.user, content_type=self.location_ct, object_id=other.id, image=first.image.name
        )
        shared_name = first.image.name

        with self.captureOnCommitCallbacks(execute=True):
            first.delete()
        self.assertTrue(default_storage.exists(shared_name))

        with self.captureOnCommitCallbacks(execute=True):
            second.delete()
        self.assertFalse(default_storage.exists(shared_name))

    def test_deleting_the_owner_removes_their_files(self):
        image_name = self.add_image().image.name
        attachment_name = self.add_attachment().file.name

        with self.captureOnCommitCallbacks(execute=True):
            self.user.delete()

        self.assertFalse(default_storage.exists(image_name))
        self.assertFalse(default_storage.exists(attachment_name))

    def test_deleting_a_visit_removes_the_files_attached_to_it(self):
        visit = Visit.objects.create(location=self.location, start_date=None)
        image_name = self.add_image(visit).image.name

        with self.captureOnCommitCallbacks(execute=True):
            visit.delete()

        self.assertFalse(default_storage.exists(image_name))

    def test_deleting_a_lodging_removes_its_files(self):
        lodging = Lodging.objects.create(user=self.user, name='Hut')
        image_name = self.add_image(lodging).image.name
        attachment_name = self.add_attachment(lodging).file.name

        with self.captureOnCommitCallbacks(execute=True):
            lodging.delete()

        self.assertFalse(default_storage.exists(image_name))
        self.assertFalse(default_storage.exists(attachment_name))

    def test_deleting_an_activity_removes_its_gpx_file(self):
        trip = Collection.objects.create(user=self.user, name='Walks')
        activity = Activity(user=self.user, collection=trip, name='Walk')
        activity.gpx_file.save('walk.gpx', ContentFile(b'<gpx/>'), save=True)
        name = activity.gpx_file.name
        self.assertTrue(default_storage.exists(name))

        with self.captureOnCommitCallbacks(execute=True):
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

        with self.captureOnCommitCallbacks(execute=True):
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
