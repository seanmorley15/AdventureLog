"""The device's own totals win over what the points say, and each field names its source."""

import io
from datetime import timedelta

from django.test import SimpleTestCase

from adventures.services.activities import analyze_track, normalize_sport_type, read_track
from adventures.tests.activities.factories import hill, make_fit, make_gpx, make_kml, make_tcx, walk


def analyze(data):
    return analyze_track(read_track(io.BytesIO(data)))


class AnalysisTests(SimpleTestCase):
    def test_gpx_fills_everything_from_the_points(self):
        result = analyze(make_gpx(walk(601, speed=1.4, ele=hill, hr=lambda i: 140 + i // 100)))
        values = result.values
        self.assertAlmostEqual(values['distance'], 840.0, delta=2)
        self.assertAlmostEqual(values['elevation_gain'], 100.0, delta=5)
        self.assertEqual(values['elapsed_time'], timedelta(seconds=600))
        self.assertAlmostEqual(values['average_speed'], 1.4, delta=0.05)
        self.assertEqual(values['sport_type'], 'Hike')
        self.assertEqual(values['name'], 'Morning Hike')
        self.assertEqual(values['max_heart_rate'], 146)
        self.assertEqual(set(result.sources.values()), {'computed'})
        self.assertEqual(result.warnings, [])

    def test_fit_device_totals_win_over_computed_ones(self):
        samples = walk(601, speed=1.4, ele=hill)
        result = analyze(make_fit(samples, ascent=137, descent=12, calories=420, total_distance=1000.0))
        self.assertEqual(result.values['elevation_gain'], 137)
        self.assertEqual(result.values['elevation_loss'], 12)
        self.assertAlmostEqual(result.values['distance'], 1000.0, delta=0.1)
        self.assertEqual(result.values['calories'], 420)
        self.assertEqual(result.sources['elevation_gain'], 'device')
        self.assertEqual(result.sources['distance'], 'device')
        # Altitude extremes have no device total, so they come from the points.
        self.assertEqual(result.sources['elev_high'], 'computed')

    def test_a_missing_device_total_falls_back_to_the_points(self):
        result = analyze(make_fit(walk(601, ele=hill)))  # the session leaves ascent unset
        self.assertEqual(result.sources['elevation_gain'], 'computed')
        self.assertAlmostEqual(result.values['elevation_gain'], 100.0, delta=5)

    def test_tcx_lap_totals_win(self):
        result = analyze(make_tcx(walk(120), total_seconds=300, distance=4000.0, calories=99))
        self.assertEqual(result.values['distance'], 4000.0)
        self.assertEqual(result.values['elapsed_time'], timedelta(seconds=300))
        self.assertEqual(result.values['sport_type'], 'Run')

    def test_a_file_without_times_warns_and_skips_time_fields(self):
        result = analyze(make_kml(walk(120)))
        self.assertIn('no_timestamps', result.warnings)
        for field in ('moving_time', 'elapsed_time', 'average_speed', 'max_speed', 'start_date'):
            self.assertNotIn(field, result.values)
        self.assertIn('distance', result.values)

    def test_a_file_without_altitude_warns(self):
        result = analyze(make_gpx(walk(120, ele=lambda i: None)))
        self.assertIn('no_elevation', result.warnings)
        self.assertNotIn('elevation_gain', result.values)

    def test_the_start_point_and_end_point_are_the_first_and_last_positions(self):
        result = analyze(make_gpx(walk(601, speed=1.4)))
        self.assertAlmostEqual(result.values['start_lat'], 41.0, places=4)
        self.assertGreater(result.values['end_lat'], result.values['start_lat'])

    def test_rest_time_is_elapsed_minus_moving(self):
        result = analyze(make_tcx(walk(120)))
        values = result.values
        self.assertEqual(values['rest_time'], values['elapsed_time'] - values['moving_time'])


class SportTests(SimpleTestCase):
    def test_other_apps_names_map_onto_our_choices(self):
        cases = {
            'Kitesurf': 'Kitesurfing', 'Windsurf': 'Windsurfing', 'Sail': 'Sailing', 'Surf': 'Surfing',
            'HighIntensityIntervalTraining': 'HIIT', 'Biking': 'Ride', 'running': 'Run', 'trail': 'TrailRun',
            'mountain': 'MountainBikeRide', 'Hike': 'Hike', 'cross_country_skiing': 'NordicSki',
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_sport_type(raw), expected)

    def test_unknown_names_fall_back_to_general(self):
        self.assertEqual(normalize_sport_type('Padel', 'JumpRope', None), 'General')

    def test_the_most_specific_name_wins(self):
        self.assertEqual(normalize_sport_type('trail', 'running'), 'TrailRun')
        self.assertEqual(normalize_sport_type('generic', 'cycling'), 'Ride')
