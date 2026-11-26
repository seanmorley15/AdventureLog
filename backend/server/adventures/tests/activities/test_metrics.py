"""Distance, elevation, time and speed worked out from recorded points."""

import math
from datetime import timedelta

from django.test import SimpleTestCase

from adventures.services.activities import metrics
from adventures.services.activities.sports import stopped_speed_for
from adventures.tests.activities.factories import Sample, hill, noisy_flat, points, walk


class DistanceTests(SimpleTestCase):
    def test_a_straight_walk_measures_speed_times_time(self):
        track = [points(walk(601, speed=1.4))]
        self.assertAlmostEqual(metrics.distance(track), 840.0, delta=1.0)

    def test_standing_still_adds_no_distance(self):
        # Wobble of half a meter around one spot, like GPS noise at a rest stop.
        samples = [Sample(i, 0.5 * math.sin(i)) for i in range(120)]
        self.assertLess(metrics.distance([points(samples)]), 1.0)

    def test_the_gap_between_segments_is_not_counted(self):
        first = points(walk(100, speed=1.0))
        second = points([Sample(500 + s.seconds, 5000 + s.north) for s in walk(100, speed=1.0)])
        self.assertAlmostEqual(metrics.distance([first, second]), 198.0, delta=2.0)


class ElevationTests(SimpleTestCase):
    def test_noise_on_flat_ground_is_not_a_climb(self):
        gain, loss, _high, _low = metrics.elevation([points(walk(600, ele=noisy_flat))])
        self.assertLess(gain, 5)
        self.assertLess(loss, 5)

    def test_a_steady_climb_counts_in_full(self):
        gain, loss, high, low = metrics.elevation([points(walk(600, ele=hill))])
        self.assertAlmostEqual(gain, 100.0, delta=4.0)
        self.assertEqual(loss, 0)
        self.assertAlmostEqual(high, 200.0, delta=1.0)
        self.assertAlmostEqual(low, 100.0, delta=1.0)

    def test_up_and_down_counts_both_ways(self):
        up_down = lambda i: 100.0 + (60.0 * i / 300 if i < 300 else 60.0 * (600 - i) / 300)
        gain, loss, _high, _low = metrics.elevation([points(walk(600, ele=up_down))])
        self.assertAlmostEqual(gain, 60.0, delta=4.0)
        self.assertAlmostEqual(loss, 60.0, delta=4.0)

    def test_a_single_altitude_spike_is_ignored(self):
        spiked = lambda i: 400.0 if i == 300 else 100.0
        gain, _loss, high, _low = metrics.elevation([points(walk(600, ele=spiked))])
        self.assertEqual(gain, 0)
        self.assertEqual(high, 100.0)

    def test_the_step_between_segments_is_not_counted(self):
        low_part = points(walk(100, ele=lambda i: 100.0))
        high_part = points(walk(100, ele=lambda i: 500.0, start=1000))
        gain, loss, _high, _low = metrics.elevation([low_part, high_part])
        self.assertEqual((gain, loss), (0, 0))

    def test_no_altitude_gives_none(self):
        self.assertIsNone(metrics.elevation([points(walk(50, ele=lambda i: None))]))


class TimeTests(SimpleTestCase):
    def test_elapsed_time_runs_first_to_last_timestamp(self):
        self.assertEqual(metrics.elapsed_time([points(walk(61))]), timedelta(seconds=60))

    def test_a_pause_is_not_moving_time(self):
        before = walk(300, speed=1.4)
        # Stand still for ten minutes, one sample a minute, then go on.
        rest = [Sample(300 + 60 * i, before[-1].north) for i in range(10)]
        after = [Sample(900 + i, before[-1].north + 1.4 * i) for i in range(300)]
        moving = metrics.moving_time([points(before + rest + after)], stopped_speed=0.5)
        self.assertAlmostEqual(moving.total_seconds(), 600, delta=15)

    def test_no_timestamps_means_no_time_metrics(self):
        untimed = points(walk(50))
        for point in untimed:
            point.time = None
        self.assertIsNone(metrics.moving_time([untimed], 0.5))
        self.assertIsNone(metrics.elapsed_time([untimed]))
        self.assertIsNone(metrics.max_speed([untimed]))

    def test_cycling_needs_more_speed_to_count_as_moving(self):
        self.assertGreater(stopped_speed_for('Ride'), stopped_speed_for('Hike'))


class MaxSpeedTests(SimpleTestCase):
    def test_a_gps_spike_does_not_set_max_speed(self):
        samples = walk(120, speed=2.0)
        samples[60] = Sample(60, samples[60].north + 100)  # one point 100 m off for one second
        self.assertAlmostEqual(metrics.max_speed([points(samples)]), 2.0, delta=1.5)

    def test_steady_speed_is_its_own_max(self):
        self.assertAlmostEqual(metrics.max_speed([points(walk(120, speed=3.0))]), 3.0, delta=0.1)
