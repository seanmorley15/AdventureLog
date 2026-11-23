"""A Strava activity imported as a track, without downloading a file from Strava first."""

import io
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import requests
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from adventures.services.activities import read_track
from integrations.errors import IntegrationError
from integrations.models import StravaToken
from integrations.services.strava import build_track
from users.models import CustomUser

ACTIVITY = {'id': 99, 'name': 'Lunch ride', 'sport_type': 'MountainBikeRide', 'start_date': '2026-06-06T10:00:00Z'}
STREAMS = {
    'latlng': {'data': [[41.0, 2.0], [41.001, 2.0], [41.002, 2.0]]},
    'altitude': {'data': [100.0, 101.0, 103.0]},
    'time': {'data': [0, 30, 60]},
    'heartrate': {'data': [120, 130, 140]},
}


class BuildTrackTests(SimpleTestCase):
    def test_streams_become_timed_points_with_heart_rate(self):
        track = build_track(ACTIVITY, STREAMS)
        self.assertEqual((track.name, track.sport), ('Lunch ride', 'MountainBikeRide'))
        points = track.points
        self.assertEqual(len(points), 3)
        self.assertEqual(points[2].time, datetime(2026, 6, 6, 10, 1, tzinfo=timezone.utc))
        self.assertEqual((points[1].ele, points[1].heart_rate), (101.0, 130))
        self.assertIsNone(points[0].cadence)

    def test_a_stream_of_the_wrong_length_is_not_guessed_at(self):
        track = build_track(ACTIVITY, {**STREAMS, 'altitude': {'data': [100.0]}})
        self.assertTrue(all(point.ele is None for point in track.points))

    def test_an_activity_without_gps_is_unavailable(self):
        with self.assertRaises(IntegrationError) as caught:
            build_track(ACTIVITY, {'time': {'data': [0, 1]}})
        self.assertEqual(caught.exception.code, 'strava.gpx_unavailable')


def _response(status_code, payload):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    return response


class StravaGpxEndpointTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='strava-gpx', email='strava-gpx@example.com', password='testpassword123'
        )
        StravaToken.objects.create(
            user=self.user, access_token='token', refresh_token='refresh', expires_at=int(time.time()) + 3600
        )
        self.client.force_authenticate(user=self.user)

    @patch('integrations.views.strava.requests.get')
    def test_it_returns_a_gpx_built_from_the_streams(self, get):
        get.side_effect = [_response(200, ACTIVITY), _response(200, STREAMS)]
        response = self.client.get('/api/integrations/strava/activities/99/gpx/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response['Content-Type'], 'application/gpx+xml')
        track = read_track(io.BytesIO(response.content))
        self.assertEqual((len(track.points), track.sport), (3, 'MountainBikeRide'))
        self.assertEqual(get.call_args_list[1].kwargs['params']['key_by_type'], 'true')

    @patch('integrations.views.strava.requests.get')
    def test_an_indoor_activity_without_streams_is_a_404(self, get):
        get.side_effect = [_response(200, ACTIVITY), _response(404, {})]
        response = self.client.get('/api/integrations/strava/activities/99/gpx/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], 'strava.gpx_unavailable')

    @patch('integrations.views.strava.requests.get', side_effect=requests.ConnectionError)
    def test_strava_being_down_is_a_502(self, _get):
        response = self.client.get('/api/integrations/strava/activities/99/gpx/')
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()['code'], 'strava.connection_failed')

    @patch('integrations.views.strava.requests.get')
    def test_the_activity_list_no_longer_invents_an_elevation_loss(self, get):
        get.return_value = _response(200, [{
            **ACTIVITY, 'type': 'Ride', 'sport_type': 'Kitesurf', 'total_elevation_gain': 50, 'elev_high': 90, 'elev_low': 10,
        }])
        activity = self.client.get('/api/integrations/strava/activities/').json()['activities'][0]
        self.assertEqual(activity['id'], '99')
        self.assertNotIn('estimated_elevation_loss', activity)
        self.assertEqual(activity['sport_type'], 'Kitesurfing')
        self.assertEqual(activity['export_gpx'], '/api/integrations/strava/activities/99/gpx/')
