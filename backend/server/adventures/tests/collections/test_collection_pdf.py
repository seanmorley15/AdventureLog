from datetime import date, time, timedelta

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
from adventures.services.exports.pdf import build_collection_pdf, pdf_filename_for_collection
from adventures.services.exports.pdf.text import _iter_text_chunks

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
            type=Collection.Type.TRIP,
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
        self.assertEqual(pdf_filename_for_collection(collection), 'Alpine_Loop_trip_book.pdf')

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
            type=Collection.Type.TRIP,
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


# --- the Trip Book and Field Guide ---------------------------------------------------------------

import io
import logging
from datetime import datetime
from decimal import Decimal
from unittest import mock

from django.contrib.gis.geos import Point
from django.test import override_settings
from django.utils import timezone
from PIL import Image as PILImage
from pypdf import PdfReader
from rest_framework.test import APIClient

from adventures.models import Category, Checklist, ChecklistItem, Lodging, Transportation, Visit
from adventures.services.exports.pdf import PdfOptions, get_collection_for_pdf
from adventures.services.exports.pdf import maps
from adventures.services.exports.pdf.data import cost_summary
from adventures.services.exports.pdf.folder import group_places
from adventures.services.exports.pdf.media import MediaCache

A4_SIZE = (595, 842)
LETTER_SIZE = (612, 792)


def pdf_text(data: bytes) -> str:
    # pypdf cannot read the emoji font's text map and says so for every icon; the text is fine.
    logging.getLogger('pypdf').setLevel(logging.CRITICAL)
    return '\n'.join(page.extract_text() for page in PdfReader(io.BytesIO(data)).pages)


def page_sizes(data: bytes) -> set:
    return {(round(float(p.mediabox.width)), round(float(p.mediabox.height))) for p in PdfReader(io.BytesIO(data)).pages}


class BookFixtureMixin:
    """A trip with a flight, a stay, places on two days, a note and a checklist; and a folder of places."""

    def make_users(self):
        self.user = User.objects.create_user(username='bookuser', password='testpass123', first_name='Sam')
        self.friend = User.objects.create_user(username='bookfriend', password='testpass123', first_name='Alex')

    def make_trip(self):
        start = date(2026, 6, 12)
        trip = Collection.objects.create(
            user=self.user, name='Paris in June', type=Collection.Type.TRIP,
            start_date=start, end_date=start + timedelta(days=2),
            description='Museums and long walks.',
        )
        trip.shared_with.add(self.friend)
        food = Category.objects.create(user=self.user, name='food', display_name='Restaurant', icon='🍽')
        self.eiffel = Location.objects.create(
            user=self.user, name='Eiffel Tower', category=food, coordinates=Point(2.2945, 48.8584),
            description='Book the summit.', rating=4.5, price=31, location='Champ de Mars',
        )
        self.louvre = Location.objects.create(user=self.user, name='Louvre Museum', coordinates=Point(2.3376, 48.8606))
        trip.locations.add(self.eiffel, self.louvre)
        self.hotel = Lodging.objects.create(
            user=self.user, collection=trip, name='Hotel du Marais', type='hotel', location='12 Rue Vieille du Temple',
            coordinates=Point(2.3499, 48.8530), reservation_number='HDM-48213', price=540, price_currency='EUR',
            check_in=timezone.make_aware(datetime(2026, 6, 12, 15)), check_out=timezone.make_aware(datetime(2026, 6, 15, 11)),
        )
        self.flight = Transportation.objects.create(
            user=self.user, collection=trip, type='plane', name='Air France', flight_number='AF1234',
            start_code='JFK', end_code='CDG', from_location='New York', to_location='Paris',
            origin=Point(-73.78, 40.64), destination=Point(2.55, 49.01), price=780, price_currency='USD',
            date=timezone.make_aware(datetime(2026, 6, 11, 22, 30)), end_date=timezone.make_aware(datetime(2026, 6, 12, 11, 45)),
        )
        note = Note.objects.create(user=self.user, collection=trip, name='Reminders', content='Bring passport copies.', date=start)
        checklist = Checklist.objects.create(user=self.user, collection=trip, name='Packing')
        ChecklistItem.objects.create(user=self.user, checklist=checklist, name='Passport', is_checked=True)
        ChecklistItem.objects.create(user=self.user, checklist=checklist, name='Adapter')
        for offset in range(3):
            CollectionItineraryDay.objects.create(collection=trip, date=start + timedelta(days=offset), name=['Arrival', 'Museums', ''][offset])
        place = lambda model, obj, day, order, **kw: CollectionItineraryItem.objects.create(
            collection=trip, content_type=ContentType.objects.get_for_model(model), object_id=obj.id,
            date=start + timedelta(days=day), order=order, is_global=False, **kw)
        place(Transportation, self.flight, 0, 0)
        place(Lodging, self.hotel, 0, 1)
        place(Location, self.eiffel, 0, 2, start_time=time(17, 30))
        place(Location, self.louvre, 1, 0, is_optional=True)
        place(Note, note, 1, 1)
        CollectionItineraryItem.objects.create(
            collection=trip, content_type=ContentType.objects.get_for_model(Checklist), object_id=checklist.id, order=0, is_global=True,
        )
        return trip

    def make_folder(self):
        folder = Collection.objects.create(user=self.user, name='Best Bakeries', description='To try next time.')
        bakery = Category.objects.create(user=self.user, name='bakery', display_name='Bakery', icon='🥐')
        park = Category.objects.create(user=self.user, name='park', display_name='Park', icon='🌳')
        self.utopie = Location.objects.create(user=self.user, name='Boulangerie Utopie', category=bakery, coordinates=Point(2.37, 48.86), rating=4)
        self.luxembourg = Location.objects.create(user=self.user, name='Jardin du Luxembourg', category=park, coordinates=Point(2.33, 48.84))
        folder.locations.add(self.utopie, self.luxembourg)
        Visit.objects.create(location=self.utopie, start_date=timezone.make_aware(datetime(2026, 3, 2)))
        Note.objects.create(user=self.user, collection=folder, name='Metro tip', content='Line 4 crosses the river.')
        return folder

    def build(self, collection, story=False, **options):
        return build_collection_pdf(
            get_collection_for_pdf(collection.id), story=story,
            options=PdfOptions(**{'paper': 'a4', 'photos': True, 'journal': False, **options}),
        )


class TripBookTests(BookFixtureMixin, TestCase):
    def setUp(self):
        self.make_users()
        self.trip = self.make_trip()

    def test_trip_book_has_the_trips_content(self):
        text = pdf_text(self.build(self.trip))
        for expected in ('Paris in June', 'TRIP BOOK', 'Overview', 'Essentials', 'Day 1', 'Day 2', 'Day 3', 'Arrival',
                         'Eiffel Tower', 'Louvre Museum', 'JFK', 'CDG', 'AF1234', 'HDM-48213', 'Hotel du Marais',
                         '5:30 PM', 'OPTIONAL', 'Passport', 'Place index', 'Sam', 'Alex'):
            self.assertIn(expected, text)

    def test_costs_are_totalled_by_currency(self):
        text = pdf_text(self.build(self.trip))
        self.assertIn('540.00 EUR', text)
        self.assertIn('811.00 USD', text)  # the flight and the Eiffel Tower

    def test_overview_links_to_the_page_each_day_starts_on(self):
        reader = PdfReader(io.BytesIO(self.build(self.trip)))
        text = '\n'.join(page.extract_text() for page in reader.pages)
        self.assertRegex(text, r'Day 1 .*p\. \d+')
        self.assertNotIn('p. –', text)  # the second pass filled every page number in
        self.assertTrue(any(o.title.startswith('Day 1') for o in reader.outline if not isinstance(o, list)))

    def test_pages_say_how_many_there_are(self):
        reader = PdfReader(io.BytesIO(self.build(self.trip)))
        self.assertIn(f'2 / {len(reader.pages)}', reader.pages[1].extract_text())

    def test_paper_size(self):
        self.assertEqual(page_sizes(self.build(self.trip, paper='a4')), {A4_SIZE})
        self.assertEqual(page_sizes(self.build(self.trip, paper='letter')), {LETTER_SIZE})

    def test_write_in_space_is_an_option(self):
        self.assertNotIn('NOTES FROM THE DAY', pdf_text(self.build(self.trip, journal=False)))
        with_lines = pdf_text(self.build(self.trip, journal=True))
        self.assertIn('NOTES FROM THE DAY', with_lines)
        self.assertIn('NOTES', with_lines.split('Place index')[-1])

    def test_a_trip_with_nothing_scheduled_lists_everything(self):
        loose = Collection.objects.create(user=self.user, name='Loose Trip', type=Collection.Type.TRIP)
        loose.locations.add(self.eiffel)
        text = pdf_text(self.build(loose))
        self.assertIn('Eiffel Tower', text)
        self.assertIn('Nothing is scheduled', text)

    def test_no_blank_last_page(self):
        reader = PdfReader(io.BytesIO(self.build(self.trip)))
        self.assertTrue(reader.pages[-1].extract_text().strip())

    def test_the_long_note_still_paginates(self):
        note = Note.objects.create(
            user=self.user, collection=self.trip, name='Everything',
            content='\n'.join(f'Line {i}: stop, meal and walking notes.' for i in range(400)),
        )
        CollectionItineraryItem.objects.create(
            collection=self.trip, content_type=ContentType.objects.get_for_model(Note), object_id=note.id,
            date=date(2026, 6, 14), order=5, is_global=False,
        )
        self.assertIn('Line 399', pdf_text(self.build(self.trip)))


class FieldGuideTests(BookFixtureMixin, TestCase):
    def setUp(self):
        self.make_users()
        self.folder = self.make_folder()

    def test_field_guide_is_a_workbook(self):
        text = pdf_text(self.build(self.folder, journal=True))
        for expected in ('FIELD GUIDE', 'Checklist', 'Boulangerie Utopie', 'Jardin du Luxembourg', 'VISITED ON', 'RATING',
                         'NOTES', 'Places to add', 'Metro tip', '1 visited'):
            self.assertIn(expected, text)
        self.assertIn('Mar 02, 2026', text)  # a place already visited has its date filled in

    def test_without_write_in_space_it_is_a_read_only_guide(self):
        text = pdf_text(self.build(self.folder, journal=False))
        self.assertIn('Boulangerie Utopie', text)
        for absent in ('VISITED ON', 'Places to add'):
            self.assertNotIn(absent, text)

    def test_filenames_tell_the_two_books_apart(self):
        trip = self.make_trip()
        self.assertEqual(pdf_filename_for_collection(self.folder), 'Best_Bakeries_field_guide.pdf')
        self.assertEqual(pdf_filename_for_collection(trip), 'Paris_in_June_trip_book.pdf')

    def test_places_are_grouped_by_category_then_country_then_not_at_all(self):
        folder = get_collection_for_pdf(self.folder.id)
        groups = group_places(list(folder.locations.all()))
        self.assertEqual([g.title for g in groups], ['Bakery', 'Park'])
        one = [l for l in folder.locations.all() if l.name == 'Boulangerie Utopie']
        self.assertEqual([g.title for g in group_places(one)], ['Places'])

    def test_an_empty_folder_still_makes_a_pdf(self):
        empty = Collection.objects.create(user=self.user, name='Empty')
        self.assertTrue(self.build(empty, journal=True).startswith(b'%PDF'))


class StoryCopyTests(BookFixtureMixin, TestCase):
    """The public reader's PDF only shows what the owner turned on."""

    def setUp(self):
        self.make_users()
        self.trip = self.make_trip()

    def test_private_details_stay_out_until_their_group_is_on(self):
        text = pdf_text(self.build(self.trip, story=True))
        for hidden in ('HDM-48213', 'AF1234', 'EUR', '48.85', 'Sam'):
            self.assertNotIn(hidden, text)

        self.trip.story_groups = {'reservations': True, 'costs': True, 'coordinates': True, 'lodging_address': True}
        self.trip.save()
        text = pdf_text(self.build(self.trip, story=True))
        for shown in ('HDM-48213', 'AF1234', '540.00 EUR', '48.85840'):
            self.assertIn(shown, text)

    def test_no_coordinates_means_no_map_pins_or_qr_codes(self):
        story = self.build(self.trip, story=True)
        with_coordinates = self.build(self.trip)
        self.assertLess(len(story), len(with_coordinates))
        reader = PdfReader(io.BytesIO(story))
        self.assertFalse(any(page.images for page in reader.pages))

    def test_private_notes_do_not_reach_the_public(self):
        Note.objects.create(user=self.user, collection=self.trip, name='Secret plan', content='hush', is_private=True)
        self.assertNotIn('Secret plan', pdf_text(self.build(self.trip, story=True)))


class PdfOptionsTests(BookFixtureMixin, TestCase):
    def setUp(self):
        self.make_users()

    def test_defaults_follow_the_person_and_the_collection(self):
        trip, folder = self.make_trip(), self.make_folder()
        self.assertEqual(PdfOptions.from_params({}, user=self.user, collection=trip), PdfOptions('a4', True, False))
        self.assertEqual(PdfOptions.from_params({}, user=self.user, collection=folder), PdfOptions('a4', True, True))
        self.user.measurement_system = 'imperial'
        self.assertEqual(PdfOptions.from_params(None, user=self.user, collection=trip).paper, 'letter')

    def test_what_was_asked_for_wins(self):
        trip = self.make_trip()
        options = PdfOptions.from_params({'paper': 'letter', 'photos': False, 'journal': True}, user=self.user, collection=trip)
        self.assertEqual(options, PdfOptions('letter', False, True))

    def test_photos_off_loads_nothing(self):
        self.assertIsNone(MediaCache(enabled=False).thumbnail(self.make_trip().locations.first()))


class CostSummaryTests(BookFixtureMixin, TestCase):
    def setUp(self):
        self.make_users()

    def test_totals_by_currency_and_kind(self):
        trip = self.make_trip()
        summary = {b['currency']: b for b in cost_summary(get_collection_for_pdf(trip.id))}
        self.assertEqual(summary['EUR']['total'], Decimal('540'))
        self.assertEqual(summary['USD']['total'], Decimal('811'))
        self.assertEqual([(l['key'], l['count']) for l in summary['USD']['lines']], [('transportation', 1), ('location', 1)])

    def test_nothing_priced_means_nothing_to_show(self):
        self.assertEqual(cost_summary(get_collection_for_pdf(self.make_folder().id)), [])


class MapTests(TestCase):
    POINTS = [maps.MapPoint(48.8584, 2.2945, '1'), maps.MapPoint(48.8867, 2.3431, '2', '#2563eb')]

    def renderer(self):
        with override_settings(PDF_MAP_TILES=True, PDF_MAP_TILE_URL='https://tiles.example/{z}/{x}/{y}.png'):
            return maps.MapRenderer()

    def test_the_view_fits_every_point_with_room_around_them(self):
        coords = [(p.lat, p.lon) for p in self.POINTS]
        zoom, cx, cy = maps.choose_view(coords, 515, 260)
        for lat, lon in coords:
            x, y = maps.world_pixel(lat, lon, zoom)
            self.assertLess(abs(x - cx), 515 / 2 - 30)
            self.assertLess(abs(y - cy), 260 / 2 - 30)
        self.assertEqual(maps.choose_view([coords[0]], 515, 260)[0], 14)  # one place: street level

    def test_a_map_is_drawn_without_a_tile_server(self):
        with override_settings(PDF_MAP_TILES=False), mock.patch.object(maps, 'fetch_tile') as fetch:
            data = maps.MapRenderer().render(self.POINTS, 515, 260, [maps.MapLeg((48.8584, 2.2945), (48.8867, 2.3431))])
        fetch.assert_not_called()
        self.assertEqual(PILImage.open(io.BytesIO(data)).size, (1030, 520))

    def test_tiles_are_used_when_they_can_be_fetched(self):
        renderer = self.renderer()
        with mock.patch.object(maps, 'fetch_tile', return_value=PILImage.new('RGB', (256, 256), (200, 220, 200))) as fetch:
            renderer.render(self.POINTS, 515, 260)
            calls = fetch.call_count
            renderer.render(self.POINTS, 515, 200)  # the same tiles again
        self.assertTrue(renderer.used_tiles)
        self.assertGreater(calls, 0)
        self.assertLessEqual(calls, maps.MAX_TILES)
        self.assertEqual(fetch.call_count, calls)  # fetched once, then remembered

    def test_one_failed_tile_switches_the_rest_of_the_book_to_plain_maps(self):
        renderer = self.renderer()
        with mock.patch.object(maps, 'fetch_tile', side_effect=OSError('no network')) as fetch:
            first = renderer.render(self.POINTS, 515, 260)
            second = renderer.render(self.POINTS[:1], 250, 180)
        self.assertEqual(fetch.call_count, 1)
        self.assertFalse(renderer.used_tiles)
        self.assertTrue(first and second)

    def test_a_book_is_still_made_when_the_tile_server_is_down(self):
        users = BookFixtureMixin()
        users.make_users()
        trip = users.make_trip()
        with override_settings(PDF_MAP_TILES=True), mock.patch.object(maps, 'fetch_tile', side_effect=OSError('down')):
            data = users.build(trip)
        self.assertTrue(data.startswith(b'%PDF'))


class PdfApiTests(BookFixtureMixin, TestCase):
    def setUp(self):
        self.make_users()
        self.trip = self.make_trip()
        self.folder = self.make_folder()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_get_takes_options_as_query_parameters(self):
        response = self.client.get(f'/api/collections/{self.trip.id}/pdf/?paper=letter&journal=true&photos=false')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(page_sizes(response.content), {LETTER_SIZE})
        self.assertIn('NOTES FROM THE DAY', pdf_text(response.content))
        self.assertIn('Paris_in_June_trip_book.pdf', response['Content-Disposition'])

    def test_get_without_options_picks_a_folder_default(self):
        response = self.client.get(f'/api/collections/{self.folder.id}/pdf/')
        self.assertEqual(page_sizes(response.content), {A4_SIZE})
        self.assertIn('VISITED ON', pdf_text(response.content))
        self.assertIn('Best_Bakeries_field_guide.pdf', response['Content-Disposition'])

    def test_bad_options_are_refused(self):
        self.assertEqual(self.client.get(f'/api/collections/{self.trip.id}/pdf/?paper=a3').status_code, 400)
        response = self.client.post(f'/api/collections/{self.trip.id}/pdf/', {'paper': 'tabloid'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_post_hands_the_options_to_the_background_job(self):
        from jobs.models import BackgroundJob

        response = self.client.post(
            f'/api/collections/{self.trip.id}/pdf/', {'paper': 'letter', 'photos': False, 'journal': True}, format='json',
        )
        self.assertEqual(response.status_code, 202)
        params = BackgroundJob.objects.get(pk=response.json()['id']).params
        self.assertEqual(params['options'], {'paper': 'letter', 'photos': False, 'journal': True})

    def test_post_without_a_body_leaves_the_choices_to_the_job(self):
        from jobs.models import BackgroundJob

        response = self.client.post(f'/api/collections/{self.folder.id}/pdf/')
        self.assertEqual(response.status_code, 202)
        self.assertEqual(BackgroundJob.objects.get(pk=response.json()['id']).params['options'], {'photos': True, 'journal': None})
