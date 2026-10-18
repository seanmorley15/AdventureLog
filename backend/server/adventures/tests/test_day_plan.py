import importlib
import io
import json
import zipfile
from datetime import date, datetime, time, timezone

from django.apps import apps as global_apps
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from adventures.models import (
    Checklist,
    Collection,
    CollectionItineraryDay,
    CollectionItineraryItem,
    Location,
    Lodging,
    Note,
    Transportation,
    Visit,
)
from adventures.utils.collection_type import BACKUP_SCHEMA
from adventures.utils.itinerary_days import convert_collection
from users.models import CustomUser


def utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def ct(model):
    return ContentType.objects.get_for_model(model)


class DayPlanTestBase(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='day-plan-user', email='day-plan@example.com', password='testpassword123'
        )
        self.client.force_authenticate(user=self.user)

    def make_trip(self, start=date(2026, 6, 1), end=date(2026, 6, 5), **kwargs):
        return Collection.objects.create(user=self.user, name='Trip', type='trip', start_date=start, end_date=end, **kwargs)

    def location(self, name='Museum', collection=None):
        location = Location.objects.create(user=self.user, name=name)
        if collection is not None:
            location.collections.add(collection)
        return location

    def row(self, collection, obj, *, on=None, is_global=False, order=0):
        return CollectionItineraryItem.objects.create(
            collection=collection,
            content_type=ct(type(obj)),
            object_id=obj.id,
            date=on,
            is_global=is_global,
            order=order,
        )

    def days(self, collection):
        return list(collection.itinerary_days.filter(index__isnull=False).order_by('index'))

    def placements(self, collection, obj):
        return list(
            CollectionItineraryItem.objects.filter(collection=collection, object_id=obj.id)
            .select_related('day')
            .order_by('day__index')
        )

    def day(self, collection, index):
        return CollectionItineraryDay.objects.get(collection=collection, index=index)


class ConversionTests(DayPlanTestBase):
    def test_short_trip_builds_days_with_one_spanning_lodging_and_collapsed_stops(self):
        trip = self.make_trip()
        CollectionItineraryDay.objects.create(collection=trip, date=date(2026, 6, 2), name='Old town', description='Walk')
        museum = self.location('Museum', trip)
        visit = Visit.objects.create(location=museum, start_date=utc(2026, 6, 2), end_date=utc(2026, 6, 3))
        for day in (date(2026, 6, 2), date(2026, 6, 3)):
            self.row(trip, museum, on=day, order=0)
        hotel = Lodging.objects.create(
            user=self.user, name='Hotel', collection=trip,
            check_in=utc(2026, 6, 1, 15), check_out=utc(2026, 6, 4, 11), timezone='UTC',
        )
        self.row(trip, hotel, on=date(2026, 6, 1), order=0)

        self.assertTrue(convert_collection(trip))

        days = self.days(trip)
        self.assertEqual([d.index for d in days], [1, 2, 3, 4, 5])
        self.assertEqual([d.date for d in days], [date(2026, 6, d) for d in range(1, 6)])
        self.assertEqual(days[1].name, 'Old town')
        self.assertEqual(days[1].description, 'Walk')

        hotel_rows = self.placements(trip, hotel)
        self.assertEqual(len(hotel_rows), 1)
        self.assertEqual(hotel_rows[0].day.index, 1)
        self.assertEqual(hotel_rows[0].span_end_index, 3)

        museum_rows = self.placements(trip, museum)
        self.assertEqual(len(museum_rows), 1)
        self.assertEqual(museum_rows[0].day.index, 2)
        self.assertEqual(museum_rows[0].span_end_index, 3)

        visit.refresh_from_db()
        self.assertEqual(visit.start_date, utc(2026, 6, 2))
        self.assertEqual(Visit.objects.count(), 1)
        hotel.refresh_from_db()
        self.assertEqual(hotel.check_in, utc(2026, 6, 1, 15))

        trip.refresh_from_db()
        self.assertEqual(trip.start_date, date(2026, 6, 1))
        self.assertEqual(trip.end_date, date(2026, 6, 5))

    def test_conversion_is_idempotent(self):
        trip = self.make_trip()
        museum = self.location('Museum', trip)
        self.row(trip, museum, on=date(2026, 6, 2))
        self.assertTrue(convert_collection(trip))
        snapshot = list(CollectionItineraryItem.objects.values_list('id', 'day_id', 'order', 'span_end_index'))
        self.assertFalse(convert_collection(trip))
        self.assertEqual(
            list(CollectionItineraryItem.objects.values_list('id', 'day_id', 'order', 'span_end_index')),
            snapshot,
        )
        self.assertEqual(len(self.days(trip)), 5)

    def test_global_location_with_in_range_visit_appears_once(self):
        trip = self.make_trip()
        park = self.location('Park', trip)
        Visit.objects.create(location=park, start_date=utc(2026, 6, 3), end_date=utc(2026, 6, 3))
        global_row = self.row(trip, park, is_global=True)

        convert_collection(trip)

        rows = self.placements(trip, park)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].id, global_row.id)
        self.assertFalse(rows[0].is_global)
        self.assertEqual(rows[0].day.index, 3)

    def test_location_whose_only_visit_is_outside_the_range_goes_to_ideas(self):
        trip = self.make_trip()
        castle = self.location('Castle', trip)
        visit = Visit.objects.create(location=castle, start_date=utc(2025, 1, 1), end_date=utc(2025, 1, 2))

        convert_collection(trip)

        rows = self.placements(trip, castle)
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0].day_id)
        self.assertFalse(rows[0].is_global)
        visit.refresh_from_db()
        self.assertEqual((visit.start_date, visit.end_date), (utc(2025, 1, 1), utc(2025, 1, 2)))

    def test_notes_checklists_and_undated_records(self):
        trip = self.make_trip()
        global_note = Note.objects.create(user=self.user, name='Packing', collection=trip)
        self.row(trip, global_note, is_global=True)
        dated_note = Note.objects.create(user=self.user, name='Tickets', collection=trip, date=date(2026, 6, 4))
        far_note = Note.objects.create(user=self.user, name='Later', collection=trip, date=date(2026, 9, 1))
        checklist = Checklist.objects.create(user=self.user, name='Todo', collection=trip)
        undated_hotel = Lodging.objects.create(user=self.user, name='TBD', collection=trip)
        undated_flight = Transportation.objects.create(user=self.user, name='Flight', type='plane', collection=trip)

        convert_collection(trip)

        self.assertTrue(self.placements(trip, global_note)[0].is_global)
        self.assertEqual(self.placements(trip, dated_note)[0].day.index, 4)
        for obj in (far_note, checklist, undated_hotel, undated_flight):
            rows = self.placements(trip, obj)
            self.assertEqual(len(rows), 1, obj)
            self.assertIsNone(rows[0].day_id)
            self.assertFalse(rows[0].is_global)

    def test_visit_row_is_retargeted_to_its_location(self):
        trip = self.make_trip()
        museum = self.location('Museum', trip)
        visit = Visit.objects.create(location=museum, start_date=utc(2026, 6, 2), end_date=utc(2026, 6, 2))
        CollectionItineraryItem.objects.create(
            collection=trip, content_type=ct(Visit), object_id=visit.id, date=date(2026, 6, 2), order=0
        )
        self.row(trip, museum, on=date(2026, 6, 2), order=1)

        convert_collection(trip)

        self.assertFalse(CollectionItineraryItem.objects.filter(content_type=ct(Visit)).exists())
        rows = self.placements(trip, museum)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].day.index, 2)
        self.assertTrue(Visit.objects.filter(id=visit.id).exists())

    def test_long_trip_converts_and_folder_does_not(self):
        year = self.make_trip(start=date(2026, 1, 1), end=date(2026, 12, 31))
        folder = Collection.objects.create(user=self.user, name='Folder', type='folder')
        self.location('Somewhere', folder)
        self.assertTrue(convert_collection(year))
        self.assertFalse(convert_collection(year))
        self.assertEqual(len(self.days(year)), 365)
        self.assertFalse(convert_collection(folder))
        self.assertEqual(folder.itinerary_days.count(), 0)
        self.assertEqual(folder.itinerary_items.count(), 0)

    def test_data_migration_converts_with_historical_models(self):
        trip = self.make_trip()
        self.location('Museum', trip)
        migration = importlib.import_module('adventures.migrations.0079_convert_trips_to_day_plans')
        migration.convert_trips(global_apps, None)
        migration.convert_trips(global_apps, None)
        self.assertEqual(len(self.days(trip)), 5)
        self.assertEqual(trip.itinerary_items.count(), 1)

    def test_remaining_migration_converts_a_long_trip_once(self):
        year = self.make_trip(start=date(2026, 1, 1), end=date(2026, 12, 31))
        museum = self.location('Museum', year)
        self.row(year, museum, on=date(2026, 6, 1))
        short = self.make_trip()
        convert_collection(short)

        migration = importlib.import_module('adventures.migrations.0080_convert_remaining_trips_to_day_plans')
        migration.convert_remaining_trips(global_apps, None)
        migration.convert_remaining_trips(global_apps, None)

        self.assertEqual(len(self.days(year)), 365)
        self.assertEqual(self.placements(year, museum)[0].day.index, 152)
        self.assertEqual(len(self.days(short)), 5)

    def test_visit_clean_tolerates_null_dates(self):
        museum = self.location('Museum')
        Visit(location=museum, start_date=None, end_date=None).clean()
        Visit(location=museum, start_date=utc(2026, 1, 1), end_date=None).clean()


class CollectionDayCountTests(DayPlanTestBase):
    def test_new_trip_with_five_days_and_no_anchor(self):
        response = self.client.post(
            '/api/collections/', {'name': 'Someday', 'type': 'trip', 'day_count': 5}, format='json'
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body['day_count'], 5)
        self.assertIsNone(body['start_date'])
        self.assertIsNone(body['end_date'])
        self.assertIsNone(body['status'])
        trip = Collection.objects.get(id=body['id'])
        self.assertEqual([d.index for d in self.days(trip)], [1, 2, 3, 4, 5])
        self.assertTrue(all(d.date is None for d in self.days(trip)))

    def test_day_count_with_anchor_derives_end_date(self):
        response = self.client.post(
            '/api/collections/',
            {'name': 'Week', 'type': 'trip', 'day_count': 7, 'start_date': '2026-07-01'},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['end_date'], '2026-07-07')

    def test_large_day_count_is_accepted(self):
        response = self.client.post(
            '/api/collections/', {'name': 'Long stay', 'type': 'trip', 'day_count': 400}, format='json'
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['day_count'], 400)
        self.assertIsNone(response.json()['start_date'])

    def test_mismatched_end_date_is_refused(self):
        trip = self.make_trip()
        convert_collection(trip)
        response = self.client.patch(f'/api/collections/{trip.id}/', {'end_date': '2026-06-09'}, format='json')
        self.assertEqual(response.status_code, 400, response.content)

    def test_date_change_on_day_based_trip_keeps_plan(self):
        trip = self.make_trip()
        museum = self.location('Museum', trip)
        self.row(trip, museum, on=date(2026, 6, 5))
        convert_collection(trip)
        response = self.client.patch(
            f'/api/collections/{trip.id}/', {'start_date': '2026-08-01', 'end_date': '2026-08-05'}, format='json'
        )
        self.assertEqual(response.status_code, 200, response.content)
        row = self.placements(trip, museum)[0]
        self.assertEqual(row.day.index, 5)
        self.assertEqual(row.date, date(2026, 8, 5))


class PlacementTests(DayPlanTestBase):
    def setUp(self):
        super().setUp()
        self.trip = self.make_trip()
        convert_collection(self.trip)

    def place(self, obj, kind, day_index=None, **extra):
        payload = {'collection': str(self.trip.id), 'content_type': kind, 'object_id': str(obj.id), **extra}
        if day_index is not None:
            payload['day_index'] = day_index
        return self.client.post('/api/itineraries/', payload, format='json')

    def test_dropping_a_hotel_on_day_2_writes_check_in_and_next_morning(self):
        hotel = Lodging.objects.create(user=self.user, name='Hotel', collection=self.trip)
        response = self.place(hotel, 'lodging', 2)
        self.assertEqual(response.status_code, 201, response.content)
        hotel.refresh_from_db()
        self.assertEqual(hotel.check_in, utc(2026, 6, 2))
        self.assertEqual(hotel.check_out, utc(2026, 6, 3))
        self.assertEqual(Visit.objects.count(), 0)
        self.assertEqual(response.json()['updated_object']['id'], str(hotel.id))

    def test_moving_a_hotel_keeps_its_clock_and_ideas_clears_it(self):
        hotel = Lodging.objects.create(
            user=self.user, name='Hotel', collection=self.trip,
            check_in=utc(2026, 6, 1, 15), check_out=utc(2026, 6, 2, 11), timezone='UTC',
        )
        self.place(hotel, 'lodging', 3, span_end_index=4)
        hotel.refresh_from_db()
        self.assertEqual(hotel.check_in, utc(2026, 6, 3, 15))
        self.assertEqual(hotel.check_out, utc(2026, 6, 5, 11))

        item = CollectionItineraryItem.objects.get(object_id=hotel.id)
        response = self.client.post(
            '/api/itineraries/reorder/',
            {'items': [{'id': str(item.id), 'day_index': None, 'is_global': False, 'order': 0}]},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        hotel.refresh_from_db()
        self.assertIsNone(hotel.check_in)
        self.assertIsNone(hotel.check_out)

    def test_an_item_already_on_a_day_cannot_also_sit_in_ideas(self):
        museum = self.location('Museum', self.trip)
        self.place(museum, 'location', 1)
        refused = self.place(museum, 'location')
        self.assertEqual(refused.status_code, 400, refused.content)
        self.assertEqual(refused.json()['code'], 'already_planned')
        self.assertEqual(len(self.placements(self.trip, museum)), 1)

        hotel = Lodging.objects.create(user=self.user, name='Hotel', collection=self.trip)
        self.place(hotel, 'lodging', 2)
        refused_hotel = self.place(hotel, 'lodging')
        self.assertEqual(refused_hotel.status_code, 400, refused_hotel.content)
        self.assertEqual(CollectionItineraryItem.objects.get(object_id=hotel.id).day.index, 2)

    def test_dropping_a_flight_writes_departure(self):
        flight = Transportation.objects.create(
            user=self.user, name='Flight', type='plane', collection=self.trip,
            date=utc(2026, 5, 1, 9, 30), end_date=utc(2026, 5, 1, 13), start_timezone='UTC', end_timezone='UTC',
        )
        response = self.place(flight, 'transportation', 4)
        self.assertEqual(response.status_code, 201, response.content)
        flight.refresh_from_db()
        self.assertEqual(flight.date, utc(2026, 6, 4, 9, 30))
        self.assertEqual(flight.end_date, utc(2026, 6, 4, 13))
        self.assertEqual(Visit.objects.count(), 0)

    def test_adding_a_location_does_not_create_a_visit_and_may_repeat(self):
        museum = self.location('Museum', self.trip)
        first = self.place(museum, 'location', 1, update_item_date=True)
        second = self.place(museum, 'location', 3)
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(second.status_code, 201, second.content)
        self.assertEqual(Visit.objects.count(), 0)
        self.assertEqual([r.day.index for r in self.placements(self.trip, museum)], [1, 3])

    def test_log_visit_creates_one_visit_and_removing_the_stop_keeps_it(self):
        museum = self.location('Museum', self.trip)
        item_id = self.place(museum, 'location', 2).json()['id']

        first = self.client.post(f'/api/itineraries/{item_id}/log-visited/', {}, format='json')
        self.assertEqual(first.status_code, 201, first.content)
        visit = Visit.objects.get()
        self.assertEqual(visit.start_date, utc(2026, 6, 2))
        self.assertEqual(visit.end_date, utc(2026, 6, 2))
        self.assertEqual(first.json()['item']['logged_visit'], str(visit.id))

        second = self.client.post(f'/api/itineraries/{item_id}/log-visited/', {}, format='json')
        self.assertEqual(second.status_code, 200)
        self.assertEqual(Visit.objects.count(), 1)

        removed = self.client.delete(f'/api/itineraries/{item_id}/')
        self.assertEqual(removed.status_code, 204)
        self.assertTrue(Visit.objects.filter(id=visit.id).exists())

    def test_confirm_delete_visits_removes_the_logged_visit(self):
        museum = self.location('Museum', self.trip)
        item_id = self.place(museum, 'location', 2).json()['id']
        self.client.post(f'/api/itineraries/{item_id}/log-visited/', {}, format='json')
        self.client.delete(f'/api/itineraries/{item_id}/?confirm_delete_visits=true')
        self.assertEqual(Visit.objects.count(), 0)

    def test_log_visit_links_a_visit_already_on_those_dates(self):
        museum = self.location('Museum', self.trip)
        existing = Visit.objects.create(location=museum, start_date=utc(2026, 6, 2), end_date=utc(2026, 6, 2))
        item_id = self.place(museum, 'location', 2).json()['id']

        response = self.client.post(f'/api/itineraries/{item_id}/log-visited/', {}, format='json')

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Visit.objects.count(), 1)
        self.assertEqual(response.json()['item']['logged_visit'], str(existing.id))
        self.assertFalse(response.json()['created'])

    def test_log_visit_ignores_a_visit_on_a_different_day(self):
        museum = self.location('Museum', self.trip)
        Visit.objects.create(location=museum, start_date=utc(2026, 6, 1), end_date=utc(2026, 6, 1))
        item_id = self.place(museum, 'location', 2).json()['id']

        response = self.client.post(f'/api/itineraries/{item_id}/log-visited/', {}, format='json')

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Visit.objects.count(), 2)

    def test_log_visit_without_an_anchor_needs_a_date(self):
        trip = Collection.objects.create(user=self.user, name='Loose', type='trip')
        from adventures.utils.itinerary_days import build_days

        build_days(trip, 3)
        museum = self.location('Museum', trip)
        response = self.client.post(
            '/api/itineraries/',
            {'collection': str(trip.id), 'content_type': 'location', 'object_id': str(museum.id), 'day_index': 2},
            format='json',
        )
        item_id = response.json()['id']
        missing = self.client.post(f'/api/itineraries/{item_id}/log-visited/', {}, format='json')
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(missing.json()['code'], 'date_required')
        logged = self.client.post(f'/api/itineraries/{item_id}/log-visited/', {'date': '2026-03-03'}, format='json')
        self.assertEqual(logged.status_code, 201, logged.content)
        visit = Visit.objects.get()
        self.assertEqual((visit.start_date, visit.end_date), (utc(2026, 3, 3), utc(2026, 3, 3)))

    def test_log_day_logs_remaining_non_optional_stops(self):
        a = self.location('A', self.trip)
        b = self.location('B', self.trip)
        c = self.location('C', self.trip)
        hotel = Lodging.objects.create(user=self.user, name='Hotel', collection=self.trip)
        a_id = self.place(a, 'location', 2).json()['id']
        self.place(b, 'location', 2)
        self.place(c, 'location', 2, is_optional=True)
        self.place(hotel, 'lodging', 2)
        self.client.post(f'/api/itineraries/{a_id}/log-visited/', {}, format='json')

        response = self.client.post(
            '/api/itineraries/log-day/',
            {'collection': str(self.trip.id), 'day': str(self.day(self.trip, 2).id)},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(len(response.json()['items']), 1)
        self.assertEqual(Visit.objects.filter(location=a).count(), 1)
        self.assertEqual(Visit.objects.filter(location=b).count(), 1)
        self.assertEqual(Visit.objects.filter(location=c).count(), 0)

    def test_trip_wide_is_only_for_notes_and_checklists(self):
        museum = self.location('Museum', self.trip)
        note = Note.objects.create(user=self.user, name='Plan', collection=self.trip)
        refused = self.place(museum, 'location', is_global=True)
        self.assertEqual(refused.status_code, 400)
        accepted = self.place(note, 'note', is_global=True)
        self.assertEqual(accepted.status_code, 201, accepted.content)
        self.assertTrue(accepted.json()['is_global'])

    def test_ideas_placement_without_a_day(self):
        museum = self.location('Museum', self.trip)
        response = self.place(museum, 'location')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertIsNone(response.json()['day'])
        self.assertFalse(response.json()['is_global'])

    def test_order_conflict_returns_409(self):
        a = self.location('A', self.trip)
        b = self.location('B', self.trip)
        a_id = self.place(a, 'location', 1).json()['id']
        b_id = self.place(b, 'location', 1).json()['id']
        response = self.client.post(
            '/api/itineraries/reorder/',
            {'items': [
                {'id': a_id, 'day_index': 1, 'order': 0},
                {'id': b_id, 'day_index': 1, 'order': 0},
            ]},
            format='json',
        )
        self.assertEqual(response.status_code, 409)

    def test_optional_flag_and_local_times_can_be_patched(self):
        museum = self.location('Museum', self.trip)
        item_id = self.place(museum, 'location', 1).json()['id']
        response = self.client.patch(
            f'/api/itineraries/{item_id}/',
            {'is_optional': True, 'start_time': '09:30', 'end_time': '11:00', 'timezone': 'Europe/Paris'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        item = CollectionItineraryItem.objects.get(id=item_id)
        self.assertTrue(item.is_optional)
        self.assertEqual(item.start_time, time(9, 30))
        self.assertEqual(item.timezone, 'Europe/Paris')


class DayActionTests(DayPlanTestBase):
    def setUp(self):
        super().setUp()
        self.trip = self.make_trip()
        convert_collection(self.trip)
        self.hotel = Lodging.objects.create(user=self.user, name='Hotel', collection=self.trip)
        self.client.post(
            '/api/itineraries/',
            {'collection': str(self.trip.id), 'content_type': 'lodging', 'object_id': str(self.hotel.id),
             'day_index': 2, 'span_end_index': 4},
            format='json',
        )

    def post(self, path, payload):
        return self.client.post(f'/api/itineraries/{path}/', {'collection': str(self.trip.id), **payload}, format='json')

    def hotel_span(self):
        row = CollectionItineraryItem.objects.select_related('day').get(object_id=self.hotel.id)
        return row.day.index, row.span_end_index

    def test_insert_inside_a_span_extends_it(self):
        response = self.post('days/insert', {'position': 3})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual([d.index for d in self.days(self.trip)], [1, 2, 3, 4, 5, 6])
        self.assertEqual(self.hotel_span(), (2, 5))
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.end_date, date(2026, 6, 6))
        self.hotel.refresh_from_db()
        self.assertEqual(self.hotel.check_out, utc(2026, 6, 6))

    def test_delete_inside_a_span_shrinks_it(self):
        response = self.post('days/delete', {'day': str(self.day(self.trip, 3).id)})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([d.index for d in self.days(self.trip)], [1, 2, 3, 4])
        self.assertEqual(self.hotel_span(), (2, 3))

    def test_deleting_the_span_start_moves_it_to_the_next_day(self):
        response = self.post('days/delete', {'day': str(self.day(self.trip, 2).id)})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.hotel_span(), (2, 3))
        self.hotel.refresh_from_db()
        self.assertEqual(self.hotel.check_in, utc(2026, 6, 2))
        self.assertEqual(self.hotel.check_out, utc(2026, 6, 4))

    def test_deleting_a_day_with_stops_needs_a_destination(self):
        museum = self.location('Museum', self.trip)
        self.client.post(
            '/api/itineraries/',
            {'collection': str(self.trip.id), 'content_type': 'location', 'object_id': str(museum.id), 'day_index': 5},
            format='json',
        )
        day5 = self.day(self.trip, 5)
        refused = self.post('days/delete', {'day': str(day5.id)})
        self.assertEqual(refused.status_code, 400)
        self.assertEqual(refused.json()['code'], 'destination_required')

        moved = self.post('days/delete', {'day': str(day5.id), 'destination': 'day', 'target_day': str(self.day(self.trip, 1).id)})
        self.assertEqual(moved.status_code, 200, moved.content)
        self.assertEqual(self.placements(self.trip, museum)[0].day.index, 1)

    def test_delete_to_ideas_clears_lodging_dates(self):
        flight = Transportation.objects.create(user=self.user, name='Flight', type='plane', collection=self.trip)
        self.client.post(
            '/api/itineraries/',
            {'collection': str(self.trip.id), 'content_type': 'transportation', 'object_id': str(flight.id), 'day_index': 1},
            format='json',
        )
        flight.refresh_from_db()
        self.assertIsNotNone(flight.date)
        response = self.post('days/delete', {'day': str(self.day(self.trip, 1).id), 'destination': 'ideas'})
        self.assertEqual(response.status_code, 200, response.content)
        flight.refresh_from_db()
        self.assertIsNone(flight.date)
        self.assertIsNone(self.placements(self.trip, flight)[0].day_id)

    def test_move_and_duplicate_day(self):
        museum = self.location('Museum', self.trip)
        self.client.post(
            '/api/itineraries/',
            {'collection': str(self.trip.id), 'content_type': 'location', 'object_id': str(museum.id), 'day_index': 5},
            format='json',
        )
        day5 = self.day(self.trip, 5)
        moved = self.post('days/move', {'day': str(day5.id), 'position': 1})
        self.assertEqual(moved.status_code, 200, moved.content)
        self.assertEqual(self.placements(self.trip, museum)[0].day.index, 1)

        duplicated = self.post('days/duplicate', {'day': str(day5.id)})
        self.assertEqual(duplicated.status_code, 201, duplicated.content)
        self.assertEqual([r.day.index for r in self.placements(self.trip, museum)], [1, 2])
        self.assertEqual(CollectionItineraryItem.objects.filter(object_id=self.hotel.id).count(), 1)

    def test_duration_shortening_into_a_stop_uses_the_delete_prompt(self):
        museum = self.location('Museum', self.trip)
        self.client.post(
            '/api/itineraries/',
            {'collection': str(self.trip.id), 'content_type': 'location', 'object_id': str(museum.id), 'day_index': 5},
            format='json',
        )
        refused = self.post('duration', {'day_count': 3})
        self.assertEqual(refused.status_code, 400)
        self.assertEqual(refused.json()['code'], 'destination_required')

        shortened = self.post('duration', {'day_count': 3, 'destination': 'ideas'})
        self.assertEqual(shortened.status_code, 200, shortened.content)
        self.assertEqual(shortened.json()['collection']['day_count'], 3)
        self.assertEqual(shortened.json()['collection']['end_date'], '2026-06-03')
        self.assertEqual(self.hotel_span(), (2, 3))
        self.assertIsNone(self.placements(self.trip, museum)[0].day_id)

    def test_duration_extends_and_rejects_raw_end_date(self):
        extended = self.post('duration', {'day_count': 8})
        self.assertEqual(extended.status_code, 200, extended.content)
        self.assertEqual(extended.json()['collection']['end_date'], '2026-06-08')
        mismatch = self.post('duration', {'day_count': 8, 'end_date': '2026-06-20'})
        self.assertEqual(mismatch.status_code, 400)
        extended_far = self.post('duration', {'day_count': 400})
        self.assertEqual(extended_far.status_code, 200, extended_far.content)
        self.assertEqual(extended_far.json()['collection']['day_count'], 400)

    def test_setting_an_anchor_fills_lodging(self):
        trip = Collection.objects.create(user=self.user, name='Loose', type='trip')
        from adventures.utils.itinerary_days import build_days

        build_days(trip, 4)
        hotel = Lodging.objects.create(user=self.user, name='Inn', collection=trip)
        self.client.post(
            '/api/itineraries/',
            {'collection': str(trip.id), 'content_type': 'lodging', 'object_id': str(hotel.id), 'day_index': 2},
            format='json',
        )
        hotel.refresh_from_db()
        self.assertIsNone(hotel.check_in)

        response = self.client.post(
            '/api/itineraries/duration/',
            {'collection': str(trip.id), 'day_count': 4, 'start_date': '2026-10-10', 'timezone': 'Europe/Paris'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        hotel.refresh_from_db()
        self.assertEqual(hotel.check_in, utc(2026, 10, 11))
        self.assertEqual(hotel.check_out, utc(2026, 10, 12))
        trip.refresh_from_db()
        self.assertEqual(trip.timezone, 'Europe/Paris')
        self.assertEqual(trip.end_date, date(2026, 10, 13))

    def test_plan_by_days_for_a_long_trip(self):
        year = self.make_trip(start=date(2026, 1, 1), end=date(2026, 12, 31))
        museum = self.location('Museum', year)
        self.row(year, museum, on=date(2026, 1, 3))
        far = self.location('Far', year)
        self.row(year, far, on=date(2026, 6, 1))

        response = self.client.post('/api/itineraries/plan-by-days/', {'collection': str(year.id)}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(len(self.days(year)), 365)
        self.assertEqual(self.placements(year, museum)[0].day.index, 3)
        self.assertEqual(self.placements(year, far)[0].day.index, 152)
        year.refresh_from_db()
        self.assertEqual(year.end_date, date(2026, 12, 31))

        longer = self.make_trip(start=date(2026, 1, 1), end=date(2026, 3, 1))
        counted = self.client.post(
            '/api/itineraries/plan-by-days/', {'collection': str(longer.id), 'day_count': 400}, format='json'
        )
        self.assertEqual(counted.status_code, 200, counted.content)
        self.assertEqual(len(self.days(longer)), 400)

    def test_shared_user_can_change_days(self):
        friend = CustomUser.objects.create_user(username='friend', email='friend@example.com', password='pw12345678')
        self.trip.shared_with.add(friend)
        self.client.force_authenticate(user=friend)
        response = self.post('days/insert', {})
        self.assertEqual(response.status_code, 201, response.content)

        stranger = CustomUser.objects.create_user(username='stranger', email='s@example.com', password='pw12345678')
        self.client.force_authenticate(user=stranger)
        refused = self.post('days/insert', {})
        self.assertEqual(refused.status_code, 403)


class DayPlanBackupTests(DayPlanTestBase):
    def _import(self, content):
        return self.client.post(
            '/api/backup/import/',
            {'file': SimpleUploadedFile('backup.zip', content, content_type='application/zip'), 'confirm': 'yes'},
            format='multipart',
        )

    def test_schema_3_round_trip_keeps_days_spans_and_flags(self):
        trip = self.make_trip(timezone='Asia/Tokyo')
        convert_collection(trip)
        day2 = self.day(trip, 2)
        day2.name = 'Arrival'
        day2.save()
        museum = self.location('Museum', trip)
        hotel = Lodging.objects.create(user=self.user, name='Hotel', collection=trip)
        CollectionItineraryItem.objects.create(
            collection=trip, content_type=ct(Location), object_id=museum.id, day=day2, date=day2.date,
            order=0, is_optional=True, start_time=time(10, 0),
        )
        CollectionItineraryItem.objects.create(
            collection=trip, content_type=ct(Lodging), object_id=hotel.id, day=day2, date=day2.date,
            order=1, span_end_index=4,
        )

        exported = self.client.get('/api/backup/export/')
        with zipfile.ZipFile(io.BytesIO(exported.content)) as zipf:
            data = json.loads(zipf.read('data.json'))
        self.assertEqual(data['backup_schema'], BACKUP_SCHEMA)
        self.assertEqual(BACKUP_SCHEMA, 4)
        self.assertIn('day_trails', data)
        self.assertIn('day_activities', data)
        self.assertIn('day_images', data)

        response = self._import(exported.content)
        self.assertEqual(response.status_code, 200, response.content)
        restored = Collection.objects.get(user=self.user, name='Trip')
        self.assertEqual(restored.timezone, 'Asia/Tokyo')
        self.assertEqual(len(self.days(restored)), 5)
        self.assertEqual(self.day(restored, 2).name, 'Arrival')
        museum_row = CollectionItineraryItem.objects.select_related('day').get(collection=restored, content_type=ct(Location))
        self.assertEqual(museum_row.day.index, 2)
        self.assertTrue(museum_row.is_optional)
        self.assertEqual(museum_row.start_time, time(10, 0))
        hotel_row = CollectionItineraryItem.objects.get(collection=restored, content_type=ct(Lodging))
        self.assertEqual(hotel_row.span_end_index, 4)

    def test_schema_2_import_runs_the_conversion_once(self):
        payload = {
            'backup_schema': 2,
            'version': 'v0.13.0',
            'collections': [
                {'export_id': 0, 'name': 'Short', 'type': 'trip', 'start_date': '2026-06-01', 'end_date': '2026-06-03'},
                {'export_id': 1, 'name': 'Long', 'type': 'trip', 'start_date': '2026-01-01', 'end_date': '2026-12-31'},
                {'export_id': 2, 'name': 'Box', 'type': 'folder'},
            ],
            'locations': [
                {'export_id': 0, 'name': 'Museum', 'collection_export_ids': [0], 'visits': []},
            ],
            'itinerary_items': [
                {'collection_export_id': 0, 'content_type': 'location', 'item_reference': 0,
                 'date': '2026-06-02', 'is_global': False, 'order': 0},
                {'collection_export_id': 0, 'content_type': 'location', 'item_reference': 0,
                 'date': '2026-06-03', 'is_global': False, 'order': 0},
            ],
        }
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zipf:
            zipf.writestr('data.json', json.dumps(payload))
        response = self._import(buffer.getvalue())
        self.assertEqual(response.status_code, 200, response.content)

        short = Collection.objects.get(user=self.user, name='Short')
        self.assertEqual(len(self.days(short)), 3)
        rows = list(short.itinerary_items.select_related('day'))
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0].day.index, rows[0].span_end_index), (2, 3))
        long_trip = Collection.objects.get(user=self.user, name='Long')
        self.assertEqual(len(self.days(long_trip)), 365)
        self.assertEqual(long_trip.end_date, date(2026, 12, 31))
        self.assertEqual(Collection.objects.get(user=self.user, name='Box').itinerary_days.count(), 0)
