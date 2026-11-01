from datetime import datetime, timezone

from django.test import TestCase

from adventures.models import Transportation
from adventures.services.calendar_events import get_calendar_events_for_user
from users.models import CustomUser


class TransportationCalendarEventTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='calendar-user',
            email='calendar-user@example.com',
            password='testpassword123',
        )

    def _event(self, transportation):
        events = get_calendar_events_for_user(self.user)
        return next(e for e in events if e['id'] == f'transportation-{transportation.id}')

    def test_timed_departure_at_midnight_utc_is_not_all_day(self):
        # 8:00 PM in New York on 28 October 2026 is 00:00 UTC on the 29th
        flight = Transportation.objects.create(
            user=self.user,
            type='plane',
            name='Overnight flight',
            date=datetime(2026, 10, 29, 0, 0, tzinfo=timezone.utc),
            end_date=datetime(2026, 10, 29, 8, 0, tzinfo=timezone.utc),
            start_timezone='America/New_York',
            end_timezone='Europe/London',
        )
        self.assertFalse(self._event(flight)['all_day'])

    def test_all_day_transportation_without_time_zone_stays_all_day(self):
        trip = Transportation.objects.create(
            user=self.user,
            type='car',
            name='Road trip',
            date=datetime(2026, 10, 29, 0, 0, tzinfo=timezone.utc),
            end_date=datetime(2026, 10, 30, 0, 0, tzinfo=timezone.utc),
        )
        self.assertTrue(self._event(trip)['all_day'])
