"""Every supported format reads into the same track, and anything else is refused."""

import io
import zipfile
from datetime import timedelta

from django.test import SimpleTestCase

from adventures.services.activities import UnreadableTrackError, read_track, track_to_gpx
from adventures.services.activities.reading import MAX_TRACK_FILE_BYTES
from adventures.tests.activities.factories import (
    make_fit, make_gpx, make_kml, make_kmz, make_tcx, walk,
)

SAMPLES = walk(120, hr=lambda i: 150)


def read(data):
    return read_track(io.BytesIO(data))


class ReaderTests(SimpleTestCase):
    def test_gpx_reads_points_name_sport_and_heart_rate(self):
        track = read(make_gpx(SAMPLES))
        self.assertEqual((len(track.points), track.name, track.sport), (120, 'Morning Hike', 'hiking'))
        self.assertEqual(track.points[0].heart_rate, 150)
        self.assertIsNotNone(track.points[0].time.tzinfo)

    def test_gpx_waypoints_are_not_part_of_the_track(self):
        track = read(make_gpx(SAMPLES, waypoints=[(41.5, 2.0, 2000)]))
        self.assertEqual(len(track.points), 120)

    def test_a_gpx_with_only_a_route_still_reads(self):
        route = (
            b'<?xml version="1.0"?><gpx version="1.1" creator="t" xmlns="http://www.topografix.com/GPX/1/1">'
            b'<rte><name>Plan</name><rtept lat="41" lon="2"/><rtept lat="41.1" lon="2"/></rte></gpx>'
        )
        track = read(route)
        self.assertEqual((track.name, len(track.points)), ('Plan', 2))

    def test_tcx_reads_points_sport_and_lap_totals(self):
        track = read(make_tcx(SAMPLES, sport='Biking', total_seconds=119, distance=5000.0, calories=210))
        self.assertEqual((len(track.points), track.sport), (120, 'Biking'))
        self.assertEqual(track.summary.distance, 5000.0)
        self.assertEqual(track.summary.elapsed_time, timedelta(seconds=119))
        self.assertEqual(track.summary.calories, 210)

    def test_kml_and_kmz_read_the_line(self):
        for data in (make_kml(SAMPLES), make_kmz(SAMPLES)):
            track = read(data)
            self.assertEqual((len(track.points), track.name), (120, 'Ridge walk'))
            self.assertIsNone(track.points[0].time)

    def test_fit_reads_points_session_and_offset(self):
        track = read(make_fit(SAMPLES, sport=2, ascent=33, descent=31, calories=250, utc_offset_hours=-5))
        self.assertEqual((len(track.points), track.sport), (120, 'cycling'))
        self.assertEqual((track.summary.elevation_gain, track.summary.elevation_loss), (33, 31))
        self.assertEqual(track.summary.calories, 250)
        self.assertEqual(track.summary.utc_offset, timedelta(hours=-5))
        self.assertAlmostEqual(track.points[0].lat, 41.0, places=5)

    def test_a_fit_timer_stop_splits_the_recording(self):
        track = read(make_fit(SAMPLES, pause_after=60))
        self.assertEqual([len(segment) for segment in track.segments], [60, 60])

    def test_the_format_comes_from_the_content_not_the_name(self):
        # `read_track` never sees a file name that decides anything.
        self.assertEqual(read(make_tcx(SAMPLES)).format, 'tcx')

    def test_the_gpx_writer_round_trips_a_track(self):
        original = read(make_fit(SAMPLES))
        again = read(track_to_gpx(original))
        self.assertEqual(len(again.points), len(original.points))
        self.assertEqual(again.points[10].time, original.points[10].time)
        self.assertEqual(again.points[10].heart_rate, original.points[10].heart_rate)
        self.assertAlmostEqual(again.points[10].lat, original.points[10].lat, places=6)


class RefusalTests(SimpleTestCase):
    def assertRefused(self, data):
        with self.assertRaises(UnreadableTrackError) as caught:
            read(data)
        self.assertEqual(caught.exception.code, 'activity.unreadable_track')

    def test_garbage_is_refused(self):
        self.assertRefused(b'this is not a track')
        self.assertRefused(b'')

    def test_a_pdf_renamed_is_refused(self):
        self.assertRefused(b'%PDF-1.7 not a track')

    def test_broken_xml_is_refused(self):
        self.assertRefused(b'<gpx><trk><trkseg><trkpt lat="1"')

    def test_a_gpx_without_points_is_refused(self):
        self.assertRefused(b'<?xml version="1.0"?><gpx version="1.1" creator="t"></gpx>')

    def test_a_truncated_fit_is_refused(self):
        self.assertRefused(make_fit(SAMPLES)[:200])

    def test_a_zip_without_kml_is_refused(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('notes.txt', 'hello')
        self.assertRefused(buffer.getvalue())

    def test_xml_entity_bombs_are_refused(self):
        bomb = (
            b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;">]>'
            b'<TrainingCenterDatabase><Activities><Activity Sport="Running">&b;</Activity></Activities>'
            b'</TrainingCenterDatabase>'
        )
        self.assertRefused(bomb)

    def test_oversized_files_are_refused(self):
        upload = io.BytesIO(make_gpx(SAMPLES))
        upload.size = MAX_TRACK_FILE_BYTES + 1
        with self.assertRaises(UnreadableTrackError):
            read_track(upload)
