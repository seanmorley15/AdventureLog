from datetime import date

from adventures.models import CollectionItineraryItem, Transportation
from adventures.services.calendar_events import get_calendar_events_for_user
from adventures.services.day_plan import convert_collection
from adventures.tests.day_plan.base import DayPlanTestBase, item_url, utc


class TransportAllDayTests(DayPlanTestBase):
    """A timed journey leaving at 00:00 UTC is not all-day (#1327)."""

    def event(self, transportation):
        return next(
            e for e in get_calendar_events_for_user(self.user)
            if e['type'] == 'transportation' and e['id'].endswith(str(transportation.id))
        )

    def test_a_timed_departure_at_midnight_utc_is_not_all_day(self):
        # 8:00 PM in New York on 28 October 2026 is 00:00 UTC on the 29th.
        flight = Transportation.objects.create(
            user=self.user, name='Overnight flight', type='plane',
            date=utc(2026, 10, 29), end_date=utc(2026, 10, 29, 8),
            start_timezone='America/New_York', end_timezone='Europe/London',
        )
        self.assertFalse(self.event(flight)['all_day'])

    def test_a_journey_saved_without_a_time_zone_stays_all_day(self):
        road_trip = Transportation.objects.create(
            user=self.user, name='Road trip', type='car',
            date=utc(2026, 10, 29), end_date=utc(2026, 10, 30),
        )
        self.assertTrue(self.event(road_trip)['all_day'])

    def test_a_timed_departure_at_midnight_utc_on_a_trip_day_is_not_all_day(self):
        trip = self.make_trip(start=date(2026, 10, 28), end=date(2026, 10, 30))
        convert_collection(trip)
        flight = Transportation.objects.create(
            user=self.user, name='Overnight flight', type='plane', collection=trip,
            date=utc(2026, 10, 29), end_date=utc(2026, 10, 29, 8),
            start_timezone='America/New_York', end_timezone='Europe/London',
        )
        response = self.client.post(
            item_url(trip.id),
            {'content_type': 'transportation', 'object_id': str(flight.id), 'day_index': 1},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(CollectionItineraryItem.objects.filter(object_id=flight.id).exists())

        self.assertFalse(self.event(flight)['all_day'])
