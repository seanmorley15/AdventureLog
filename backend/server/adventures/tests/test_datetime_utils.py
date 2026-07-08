from datetime import date, datetime, time, timezone as dt_timezone

from django.test import SimpleTestCase
from django.utils import timezone

from adventures.utils.datetime_utils import (
    aware_utc_from_date,
    aware_utc_from_date_and_time,
    ensure_aware_utc,
    is_all_day_bound,
    is_end_of_day_utc,
    is_midnight_utc,
    normalize_all_day_visit_dates,
)


class DatetimeUtilsTests(SimpleTestCase):
    def test_ensure_aware_utc_makes_naive_datetime_aware(self):
        naive = datetime(2026, 7, 7, 0, 0, 0)
        aware = ensure_aware_utc(naive)

        self.assertIsNotNone(aware)
        self.assertTrue(timezone.is_aware(aware))
        self.assertEqual(aware, datetime(2026, 7, 7, 0, 0, 0, tzinfo=dt_timezone.utc))

    def test_ensure_aware_utc_preserves_existing_aware_datetime(self):
        aware = datetime(2026, 7, 7, 12, 0, 0, tzinfo=dt_timezone.utc)
        self.assertEqual(ensure_aware_utc(aware), aware)

    def test_aware_utc_from_date_uses_midnight(self):
        day = date(2026, 7, 7)
        start = aware_utc_from_date(day)

        self.assertTrue(timezone.is_aware(start))
        self.assertEqual(start.time(), time.min)

    def test_aware_utc_from_date_and_time(self):
        aware = aware_utc_from_date_and_time(date(2026, 7, 7), time(9, 30))

        self.assertTrue(timezone.is_aware(aware))
        self.assertEqual(aware.time(), time(9, 30))

    def test_is_midnight_and_end_of_day_helpers(self):
        start = aware_utc_from_date(date(2026, 7, 7))
        legacy_end = aware_utc_from_date(date(2026, 7, 9), end_of_day=True)

        self.assertTrue(is_midnight_utc(start))
        self.assertTrue(is_end_of_day_utc(legacy_end))
        self.assertTrue(is_all_day_bound(legacy_end))

    def test_normalize_all_day_visit_dates_converts_legacy_end_of_day(self):
        start = aware_utc_from_date(date(2026, 7, 7))
        legacy_end = aware_utc_from_date(date(2026, 7, 9), end_of_day=True)

        normalized_start, normalized_end = normalize_all_day_visit_dates(start, legacy_end)

        self.assertEqual(normalized_start, start)
        self.assertEqual(normalized_end, aware_utc_from_date(date(2026, 7, 9)))

    def test_normalize_all_day_visit_dates_leaves_timed_visits_untouched(self):
        start = aware_utc_from_date_and_time(date(2026, 7, 7), time(9, 30))
        end = aware_utc_from_date_and_time(date(2026, 7, 7), time(17, 0))

        normalized_start, normalized_end = normalize_all_day_visit_dates(start, end)

        self.assertEqual(normalized_start, start)
        self.assertEqual(normalized_end, end)
