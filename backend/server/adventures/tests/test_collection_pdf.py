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
    _iter_text_chunks,
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

    def test_large_note_pdf_splits_across_pages(self):
        """Notes taller than a page used to raise LayoutError inside a 1-cell Table."""
        start = date.today() + timedelta(days=30)
        end = start + timedelta(days=1)
        collection = Collection.objects.create(
            user=self.user,
            name='Tour Notes',
            start_date=start,
            end_date=end,
        )
        # Many short lines overflow a page even when under the old 2000-char cap.
        line_note = Note.objects.create(
            user=self.user,
            collection=collection,
            name='Day-by-day tour log',
            content='\n'.join(f'Line {i}: stop, meal, and walking notes.' for i in range(1, 251)),
            date=start,
        )
        # A long wall of text with no blank lines must also paginate.
        wall_note = Note.objects.create(
            user=self.user,
            collection=collection,
            name='History dump',
            content=' '.join(f'Paragraph{i}' for i in range(800)),
            date=start,
        )
        note_ct = ContentType.objects.get_for_model(Note)
        CollectionItineraryItem.objects.create(
            collection=collection,
            content_type=note_ct,
            object_id=line_note.id,
            date=start,
            order=0,
            is_global=False,
        )
        CollectionItineraryItem.objects.create(
            collection=collection,
            content_type=note_ct,
            object_id=wall_note.id,
            date=start,
            order=1,
            is_global=False,
        )

        pdf_bytes = build_collection_pdf(collection)

        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
        self.assertGreater(len(pdf_bytes), 2000)

    def test_folder_collection_large_note_pdf(self):
        collection = Collection.objects.create(
            user=self.user,
            name='Research Folder',
        )
        Note.objects.create(
            user=self.user,
            collection=collection,
            name='Long research note',
            content='\n\n'.join(f'Section {i}. ' + ('details ' * 40) for i in range(1, 80)),
        )

        pdf_bytes = build_collection_pdf(collection)
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))

    def test_iter_text_chunks_splits_long_notes(self):
        many_lines = '\n'.join(f'Line {i}' for i in range(90))
        chunks = _iter_text_chunks(many_lines)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(chunks[0].startswith('Line 0'))
        self.assertIn('Line 89', chunks[-1])

        paragraphs = '\n\n'.join(f'Section {i} body' for i in range(5))
        chunks = _iter_text_chunks(paragraphs)
        self.assertEqual(len(chunks), 5)
        self.assertEqual(chunks[2], 'Section 2 body')
