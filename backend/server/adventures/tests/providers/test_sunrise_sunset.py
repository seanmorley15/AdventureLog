from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from adventures.services.sunrise_sunset.times import (
    get_sunrise_sunset_for_date,
    normalize_sunrise_sunset_date,
)


class NormalizeSunriseSunsetDateTests(SimpleTestCase):
    def test_accepts_iso_date(self):
        self.assertEqual(normalize_sunrise_sunset_date('2024-06-15'), '2024-06-15')

    def test_accepts_iso_datetime(self):
        self.assertEqual(normalize_sunrise_sunset_date('2024-06-15T14:30:00Z'), '2024-06-15')

    def test_rejects_invalid_value(self):
        self.assertIsNone(normalize_sunrise_sunset_date('not-a-date'))


@override_settings(SUNRISE_SUNSET_CACHE_TIMEOUT=3600)
class GetSunriseSunsetForDateTests(SimpleTestCase):
    @patch('adventures.services.sunrise_sunset.times.get_or_fetch_cached')
    def test_delegates_to_cache_helper(self, mock_get_or_fetch_cached):
        mock_get_or_fetch_cached.return_value = {
            'date': '2024-06-15',
            'sunrise': '5:30 AM',
            'sunset': '8:15 PM',
        }

        result = get_sunrise_sunset_for_date(40.7128, -74.0060, '2024-06-15T00:00:00Z')

        self.assertEqual(result['sunrise'], '5:30 AM')
        mock_get_or_fetch_cached.assert_called_once()
        args = mock_get_or_fetch_cached.call_args.args
        self.assertEqual(args[0], 'sunrise_sunset_v1')
        self.assertEqual(args[3], '2024-06-15')

    def test_returns_none_for_invalid_date(self):
        self.assertIsNone(get_sunrise_sunset_for_date(40.7128, -74.0060, 'invalid'))
