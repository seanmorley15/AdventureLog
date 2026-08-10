from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from adventures.models import (
    Collection,
    CollectionItineraryDay,
    CollectionItineraryItem,
    Location,
    Note,
)
from adventures.services.collection_pdf import (
    build_collection_pdf,
    pdf_filename_for_collection,
)

User = get_user_model()


class CollectionPdfTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='pdfuser', password='testpass123')

    def test_build_collection_pdf_returns_valid_pdf(self):
        start = date.today() + timedelta(days=30)
        end = start + timedelta(days=2)
        collection = Collection.objects.create(
            user=self.user,
            name='Alpine Loop',
            description='**Pack layers** and good boots.',
            start_date=start,
            end_date=end,
        )
        location = Location.objects.create(
            user=self.user,
            name='Trailhead Cafe',
            location='123 Main St',
            description='Morning coffee stop.',
        )
        collection.locations.add(location)

        CollectionItineraryDay.objects.create(
            collection=collection,
            date=start,
            name='Arrival day',
            description='Settle in and explore.',
        )

        location_ct = ContentType.objects.get_for_model(Location)
        CollectionItineraryItem.objects.create(
            collection=collection,
            content_type=location_ct,
            object_id=location.id,
            date=start,
            order=0,
            is_global=False,
        )

        note = Note.objects.create(
            user=self.user,
            collection=collection,
            name='Reminders',
            content='Bring passport copies.',
            date=start,
        )
        note_ct = ContentType.objects.get_for_model(Note)
        CollectionItineraryItem.objects.create(
            collection=collection,
            content_type=note_ct,
            object_id=note.id,
            date=start + timedelta(days=1),
            order=0,
            is_global=False,
        )

        pdf_bytes = build_collection_pdf(collection)

        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
        self.assertGreater(len(pdf_bytes), 500)
        self.assertEqual(pdf_filename_for_collection(collection), 'Alpine_Loop_itinerary.pdf')

    def test_folder_collection_pdf(self):
        collection = Collection.objects.create(
            user=self.user,
            name='Ideas Folder',
            description='Places to consider later.',
        )
        location = Location.objects.create(
            user=self.user,
            name='Museum',
            location='Downtown',
        )
        collection.locations.add(location)

        pdf_bytes = build_collection_pdf(collection)
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
