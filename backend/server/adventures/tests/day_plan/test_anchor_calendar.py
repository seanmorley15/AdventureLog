from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from adventures.models import (
    Activity,
    Collection,
    CollectionItineraryItem,
    Lodging,
    Transportation,
    Visit,
)
from adventures.services.calendar_events import get_calendar_events_for_user
from adventures.services.exports.pdf import build_collection_pdf
from adventures.services.exports.pdf.data import group_itinerary_days
from adventures.tests.day_plan.base import DayPlanTestBase, utc
from adventures.services.day_plan import build_days, convert_collection, shift_datetime
from users.models import CustomUser


class ShiftTests(DayPlanTestBase):
    def setUp(self):
        super().setUp()
        self.trip = self.make_trip()
        convert_collection(self.trip)

    def place(self, obj, kind, day_index, **extra):
        payload = {
            'collection': str(self.trip.id), 'content_type': kind, 'object_id': str(obj.id),
            'day_index': day_index, **extra,
        }
        response = self.client.post('/api/itineraries/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return CollectionItineraryItem.objects.get(pk=response.json()['id'])

    def shift(self, **body):
        return self.client.post('/api/itineraries/shift/', {'collection': str(self.trip.id), **body}, format='json')

    def test_shift_by_three_days_keeps_indexes_order_and_clock_faces(self):
        museum = self.location('Museum', self.trip)
        cafe = self.location('Cafe', self.trip)
        first = self.place(museum, 'location', 2)
        second = self.place(cafe, 'location', 2)
        hotel = Lodging.objects.create(
            user=self.user, name='Hotel', collection=self.trip,
            check_in=utc(2026, 6, 2, 15), check_out=utc(2026, 6, 4, 11), timezone='UTC',
        )
        stay = self.place(hotel, 'lodging', 2, span_end_index=3)
        flight = Transportation.objects.create(
            user=self.user, name='Flight', type='plane', collection=self.trip,
            date=utc(2026, 6, 5, 9, 30), end_date=utc(2026, 6, 5, 13),
            start_timezone='UTC', end_timezone='UTC',
        )
        self.place(flight, 'transportation', 5)
        visit = Visit.objects.create(location=museum, start_date=utc(2026, 6, 2), end_date=utc(2026, 6, 2))

        response = self.shift(days=3)
        self.assertEqual(response.status_code, 200, response.content)

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.start_date, date(2026, 6, 4))
        self.assertEqual(self.trip.end_date, date(2026, 6, 8))
        self.assertEqual([d.index for d in self.days(self.trip)], [1, 2, 3, 4, 5])
        self.assertEqual(self.day(self.trip, 2).date, date(2026, 6, 5))
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((first.day.index, first.order), (2, 0))
        self.assertEqual((second.day.index, second.order), (2, 1))
        self.assertEqual(first.date, date(2026, 6, 5))
        stay.refresh_from_db()
        self.assertEqual((stay.day.index, stay.span_end_index), (2, 3))

        hotel.refresh_from_db()
        self.assertEqual(hotel.check_in, utc(2026, 6, 5, 15))
        self.assertEqual(hotel.check_out, utc(2026, 6, 7, 11))
        flight.refresh_from_db()
        self.assertEqual(flight.date, utc(2026, 6, 8, 9, 30))
        self.assertEqual(flight.end_date, utc(2026, 6, 8, 13))

        visit.refresh_from_db()
        self.assertEqual(visit.start_date, utc(2026, 6, 2))

        # A later edit of the hotel's span does not restore the old dates.
        self.client.patch(f'/api/itineraries/{stay.id}/', {'span_end_index': 4}, format='json')
        hotel.refresh_from_db()
        self.assertEqual(hotel.check_in, utc(2026, 6, 5, 15))
        self.assertEqual(hotel.check_out, utc(2026, 6, 8, 11))

    def test_shift_to_a_start_date_and_back(self):
        response = self.shift(start_date='2026-05-30')
        self.assertEqual(response.status_code, 200, response.content)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.start_date, date(2026, 5, 30))
        back = self.shift(days=2)
        self.assertEqual(back.status_code, 200, back.content)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.start_date, date(2026, 6, 1))

    def test_shift_keeps_local_clock_across_dst(self):
        paris = ZoneInfo('Europe/Paris')
        # 09:00 in Paris the day before spring-forward (2026-03-29).
        before = datetime(2026, 3, 28, 9, tzinfo=paris).astimezone(timezone.utc)
        shifted = shift_datetime(before, 2, 'Europe/Paris')
        self.assertEqual(shifted.astimezone(paris).time(), time(9))
        self.assertEqual(shifted.astimezone(paris).date(), date(2026, 3, 30))
        # An ambiguous fall-back hour (2026-10-25 02:30) takes the first offset.
        ambiguous = shift_datetime(datetime(2026, 10, 24, 2, 30, tzinfo=paris).astimezone(timezone.utc), 1, 'Europe/Paris')
        self.assertEqual(ambiguous.astimezone(paris).utcoffset().total_seconds(), 7200)
        # All-day values move by whole dates.
        self.assertEqual(shift_datetime(utc(2026, 3, 28), 2, 'Europe/Paris'), utc(2026, 3, 30))

    def test_overnight_flight_keeps_both_zones(self):
        flight = Transportation.objects.create(
            user=self.user, name='Red-eye', type='plane', collection=self.trip,
            date=datetime(2026, 6, 3, 22, tzinfo=ZoneInfo('America/New_York')),
            end_date=datetime(2026, 6, 4, 10, tzinfo=ZoneInfo('Europe/London')),
            start_timezone='America/New_York', end_timezone='Europe/London',
        )
        self.place(flight, 'transportation', 3)
        flight.refresh_from_db()
        departure, arrival = flight.date, flight.end_date
        self.assertEqual(self.shift(days=1).status_code, 200)
        flight.refresh_from_db()
        self.assertEqual(flight.date.astimezone(ZoneInfo('America/New_York')).time(), time(22))
        self.assertEqual(flight.end_date.astimezone(ZoneInfo('Europe/London')).time(), time(10))
        self.assertEqual((flight.date - departure).days, 1)
        self.assertEqual(flight.end_date - flight.date, arrival - departure)

    def test_shift_needs_an_anchor_and_membership(self):
        loose = Collection.objects.create(user=self.user, name='Loose', type='trip')
        build_days(loose, 3)
        refused = self.client.post('/api/itineraries/shift/', {'collection': str(loose.id), 'days': 2}, format='json')
        self.assertEqual(refused.status_code, 400)
        self.assertEqual(refused.json()['code'], 'no_anchor')

        friend = CustomUser.objects.create_user(username='editor', email='editor@example.com', password='pw12345678')
        self.trip.shared_with.add(friend)
        self.client.force_authenticate(user=friend)
        self.assertEqual(self.shift(days=1).status_code, 200)

        stranger = CustomUser.objects.create_user(username='stranger', email='s@example.com', password='pw12345678')
        self.client.force_authenticate(user=stranger)
        self.assertEqual(self.shift(days=1).status_code, 403)

    def test_moving_the_anchor_in_the_duration_dialog_shifts_clocks(self):
        hotel = Lodging.objects.create(
            user=self.user, name='Hotel', collection=self.trip,
            check_in=utc(2026, 6, 2, 15), check_out=utc(2026, 6, 3, 11), timezone='UTC',
        )
        self.place(hotel, 'lodging', 2)
        response = self.client.post(
            '/api/itineraries/duration/',
            {'collection': str(self.trip.id), 'day_count': 5, 'start_date': '2026-06-11'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        hotel.refresh_from_db()
        self.assertEqual(hotel.check_in, utc(2026, 6, 12, 15))
        self.assertEqual(hotel.check_out, utc(2026, 6, 13, 11))


class CalendarTests(DayPlanTestBase):
    def setUp(self):
        super().setUp()
        self.friend = CustomUser.objects.create_user(
            username='friend', email='friend@example.com', password='pw12345678'
        )
        self.trip = self.make_trip(start=date(2026, 6, 1), end=date(2026, 6, 3))
        convert_collection(self.trip)
        self.trip.shared_with.add(self.friend)
        self.museum = self.location('Museum', self.trip)
        self.place(self.museum, 'location', 2)

    def place(self, obj, kind, day_index, **extra):
        response = self.client.post(
            '/api/itineraries/',
            {'collection': str(self.trip.id), 'content_type': kind, 'object_id': str(obj.id), 'day_index': day_index, **extra},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        return CollectionItineraryItem.objects.get(pk=response.json()['id'])

    def events(self, user):
        return get_calendar_events_for_user(user)

    def ids(self, user, prefix=''):
        return {e['id'] for e in self.events(user) if e['id'].startswith(prefix)}

    def test_owner_and_collaborator_see_one_event_per_non_optional_placement(self):
        cafe = self.location('Cafe', self.trip)
        self.place(cafe, 'location', 1, is_optional=True)
        hotel = Lodging.objects.create(user=self.user, name='Hotel', collection=self.trip)
        self.place(hotel, 'lodging', 1, span_end_index=2)
        day = self.day(self.trip, 3)
        Activity.objects.create(user=self.user, day=day, name='Ridge hike')

        for user in (self.user, self.friend):
            events = self.events(user)
            stops = [e for e in events if e['type'] == 'stop']
            self.assertEqual([e['title'] for e in stops], ['Museum'])
            self.assertEqual(stops[0]['start'], '2026-06-02')
            lodging = [e for e in events if e['type'] == 'lodging']
            self.assertEqual(len(lodging), 1)
            self.assertEqual(lodging[0]['start'][:10], '2026-06-01')
            activities = [e for e in events if e['type'] == 'activity']
            self.assertEqual([(e['title'], e['start']) for e in activities], [('Ridge hike', '2026-06-03')])

    def test_collaborator_does_not_see_the_owners_old_visit(self):
        Visit.objects.create(location=self.museum, start_date=utc(2019, 5, 1), end_date=utc(2019, 5, 1))
        self.assertEqual(len(self.ids(self.user, 'visit-')), 1)
        self.assertEqual(self.ids(self.friend, 'visit-'), set())
        self.assertEqual(len(self.ids(self.friend, 'stop-')), 1)

    def test_owner_visit_on_the_stop_date_is_one_event(self):
        Visit.objects.create(location=self.museum, start_date=utc(2026, 6, 2), end_date=utc(2026, 6, 2))
        self.assertEqual(len(self.ids(self.user, 'visit-')), 1)
        self.assertEqual(self.ids(self.user, 'stop-'), set())
        self.assertEqual(len(self.ids(self.friend, 'stop-')), 1)

    def test_archived_and_unanchored_trips_are_absent(self):
        self.assertTrue(self.ids(self.user, 'collection-'))
        self.trip.is_archived = True
        self.trip.save()
        for user in (self.user, self.friend):
            self.assertFalse([e for e in self.events(user) if e['collection_id'] == str(self.trip.id)])

        loose = Collection.objects.create(user=self.user, name='Loose', type='trip')
        build_days(loose, 3)
        hotel = Lodging.objects.create(
            user=self.user, name='Inn', collection=loose,
            check_in=utc(2026, 7, 1), check_out=utc(2026, 7, 2),
        )
        self.assertFalse([e for e in self.events(self.user) if e['collection_id'] == str(loose.id)])
        self.assertNotIn(f'lodging-{hotel.id}', self.ids(self.user))

    def test_removing_a_collaborator_drops_the_trip(self):
        self.assertTrue(self.ids(self.friend, 'stop-'))
        self.trip.shared_with.remove(self.friend)
        self.assertEqual(self.events(self.friend), [])

    def test_ics_is_private_and_omits_unanchored_trips(self):
        response = self.client.get('/api/ics-calendar/generate/')
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('CLASS:PRIVATE', body)
        self.assertNotIn('CLASS:PUBLIC', body)
        self.assertIn('Museum', body)

        self.trip.start_date = None
        self.trip.end_date = None
        self.trip.save()
        body = self.client.get('/api/ics-calendar/generate/').content.decode()
        self.assertNotIn('Museum', body)


class PdfDayTests(DayPlanTestBase):
    def test_pdf_prints_day_n_with_date_only_when_anchored(self):
        trip = self.make_trip(start=date(2026, 6, 1), end=date(2026, 6, 2))
        convert_collection(trip)
        groups, _, _ = group_itinerary_days(trip)
        self.assertEqual(len(groups), 2)
        self.assertTrue(groups[0]['display_date'].startswith('Day 1 · '))
        self.assertIn('2026', groups[1]['display_date'])

        loose = Collection.objects.create(user=self.user, name='Loose', type='trip')
        build_days(loose, 2)
        groups, _, _ = group_itinerary_days(loose)
        self.assertEqual([g['display_date'] for g in groups], ['Day 1', 'Day 2'])
        self.assertTrue(build_collection_pdf(loose).startswith(b'%PDF'))
