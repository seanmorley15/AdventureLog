from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from integrations.endurain_services import (
    IntegrationError,
    MfaRequired,
    decode_jwt_sub,
    normalize_activity,
    normalize_server_url,
)

User = get_user_model()


class EndurainServicesTest(TestCase):
    def test_normalize_server_url_strips_trailing_slash(self):
        self.assertEqual(
            normalize_server_url('https://example.com/'),
            'https://example.com',
        )

    def test_normalize_server_url_rejects_invalid(self):
        with self.assertRaises(IntegrationError):
            normalize_server_url('not-a-url')

    def test_normalize_server_url_rejects_credentials_and_metadata(self):
        with self.assertRaises(IntegrationError):
            normalize_server_url('https://user:pass@example.com')
        with self.assertRaises(IntegrationError):
            normalize_server_url('http://169.254.169.254')
        with self.assertRaises(IntegrationError):
            normalize_server_url('https://example.com?x=1')

    def test_safe_gpx_filename_strips_header_injection(self):
        from integrations.endurain_services import safe_gpx_filename

        self.assertEqual(
            safe_gpx_filename('run"; filename="evil.html'),
            'run_filenameevilhtml.gpx',
        )
        self.assertEqual(safe_gpx_filename(''), 'activity.gpx')

    def test_mfa_pending_roundtrip(self):
        from integrations.endurain_services import consume_mfa_pending, create_mfa_pending

        token = create_mfa_pending(1, 'https://example.com', 'runner')
        pending = consume_mfa_pending(1, token)
        self.assertEqual(pending['username'], 'runner')
        self.assertEqual(pending['server_url'], 'https://example.com')
        with self.assertRaises(IntegrationError):
            consume_mfa_pending(1, token)

    def test_mobile_headers_identify_adventurelog(self):
        from integrations.endurain_services import ENDURAIN_USER_AGENT, _mobile_headers

        headers = _mobile_headers()
        self.assertEqual(headers['User-Agent'], ENDURAIN_USER_AGENT)
        self.assertIn('AdventureLog Integration', headers['User-Agent'])
        self.assertEqual(headers['X-Client-Type'], 'mobile')

        authed = _mobile_headers('token-value')
        self.assertEqual(authed['Authorization'], 'Bearer token-value')
        self.assertEqual(authed['User-Agent'], ENDURAIN_USER_AGENT)

    def test_decode_jwt_sub(self):
        import base64
        import json

        payload = base64.urlsafe_b64encode(json.dumps({'sub': 42}).encode()).decode().rstrip('=')
        token = f'header.{payload}.signature'
        self.assertEqual(decode_jwt_sub(token), 42)

    def test_normalize_activity_maps_fields(self):
        activity = normalize_activity(
            {
                'id': 7,
                'name': 'Morning Run',
                'activity_type': 1,
                'distance': 5000,
                'total_timer_time': 1800,
                'total_elapsed_time': 1900,
                'elevation_gain': 120,
                'elevation_loss': 80,
                'average_speed': 2.78,
                'max_speed': 4.0,
                'start_time': '2024-06-01T08:00:00Z',
                'start_time_tz_applied': '2024-06-01T10:00:00',
                'timezone': 'Europe/Berlin',
                'calories': 400,
                'average_cad': 170,
                'average_power': 200,
                'max_power': 350,
                'tracker_model': 'Forerunner 255',
            },
            'https://endurain.example.com',
        )
        self.assertEqual(activity['id'], 7)
        self.assertEqual(activity['sport_type'], 'Run')
        self.assertEqual(activity['distance_km'], 5.0)
        self.assertEqual(activity['total_elevation_gain'], 120.0)
        self.assertEqual(activity['estimated_elevation_loss'], 80.0)
        self.assertEqual(activity['rest_time'], 100)
        self.assertEqual(activity['start_date_local'], '2024-06-01T10:00:00')
        self.assertEqual(activity['average_cadence'], 170)
        self.assertEqual(activity['average_watts'], 200)
        self.assertEqual(activity['device_name'], 'Forerunner 255')
        self.assertEqual(activity['calories'], 400)
        self.assertEqual(activity['provider'], 'endurain')
        self.assertTrue(activity['export_gpx'].endswith('/api/integrations/endurain/activities/7/gpx/'))

    def test_extract_elevations_from_stream(self):
        from integrations.endurain_services import _extract_elevations, _extract_lat_lon_points

        elev = _extract_elevations(
            {
                'stream_waypoints': [
                    {'time': 1, 'ele': 100},
                    {'time': 2, 'ele': 110},
                    {'time': 3, 'elevation': 105},
                ]
            }
        )
        self.assertEqual(elev, [100.0, 110.0, 105.0])

        points = _extract_lat_lon_points(
            {
                'stream_waypoints': [
                    {'lat': 40.0, 'lon': -74.0, 'time': '2024-06-01T08:00:00Z'},
                    {'latitude': 40.1, 'longitude': -74.1},
                ]
            }
        )
        self.assertEqual(len(points), 2)
        self.assertEqual(points[0][0], 40.0)
        self.assertEqual(points[0][1], -74.0)
        self.assertIsNotNone(points[0][2])
        self.assertIsNone(points[1][2])

    @patch('integrations.endurain_services.requests.post')
    def test_login_with_password_mfa_required(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.json.return_value = {
            'mfa_required': True,
            'username': 'runner',
        }
        mock_post.return_value = mock_response

        with self.assertRaises(MfaRequired) as ctx:
            from integrations.endurain_services import login_with_password

            login_with_password('https://endurain.example.com', 'runner', 'secret')
        self.assertEqual(ctx.exception.username, 'runner')

    @patch('integrations.endurain_services.requests.post')
    def test_login_with_password_success(self, mock_post):
        import base64
        import json
        import time

        payload = base64.urlsafe_b64encode(json.dumps({'sub': 99}).encode()).decode().rstrip('=')
        access = f'h.{payload}.s'
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': access,
            'refresh_token': 'refresh-token',
            'expires_in': 900,
            'refresh_token_expires_in': 604800,
        }
        mock_post.return_value = mock_response

        from integrations.endurain_services import login_with_password

        tokens = login_with_password('https://endurain.example.com', 'runner', 'secret')
        self.assertEqual(tokens['endurain_user_id'], 99)
        self.assertGreater(tokens['access_token_expires_at'], int(time.time()))

    @patch('integrations.endurain_services.requests.post')
    def test_verify_mfa_success(self, mock_post):
        import base64
        import json

        payload = base64.urlsafe_b64encode(json.dumps({'sub': 99}).encode()).decode().rstrip('=')
        access = f'h.{payload}.s'
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': access,
            'refresh_token': 'refresh-token',
            'expires_in': 900,
        }
        mock_post.return_value = mock_response

        from integrations.endurain_services import verify_mfa

        tokens = verify_mfa('https://endurain.example.com', 'runner', '123456')
        self.assertEqual(tokens['endurain_user_id'], 99)
        self.assertEqual(tokens['username'], 'runner')
