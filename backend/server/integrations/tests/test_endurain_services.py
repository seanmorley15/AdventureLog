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
        mock_response.is_redirect = False
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
        mock_response.is_redirect = False
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
        mock_response.is_redirect = False
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

    def test_normalize_activity_converts_utc_start_to_timezone(self):
        activity = normalize_activity(
            {
                'id': 8,
                'name': 'Evening Ride',
                'activity_type': 4,
                'distance': 1000,
                'start_time': '2024-06-01T08:00:00Z',
                'timezone': 'Europe/Berlin',
            },
            'https://endurain.example.com',
        )
        self.assertEqual(activity['start_date'], '2024-06-01T08:00:00Z')
        self.assertTrue(activity['start_date_local'].startswith('2024-06-01T10:00:00'))

    def _integration(self):
        integration = MagicMock()
        integration.endurain_user_id = 7
        return integration

    def _json_response(self, payload, status_code=200):
        response = MagicMock()
        response.status_code = status_code
        response.headers = {'Content-Type': 'application/json'}
        response.json.return_value = payload
        return response

    def _html_response(self):
        response = MagicMock()
        response.status_code = 200
        response.headers = {'Content-Type': 'text/html; charset=utf-8'}
        response.json.side_effect = ValueError('Expecting value')
        return response

    @patch('integrations.endurain_services._request')
    def test_fetch_user_activities_reads_v020_page(self, mock_request):
        from integrations.endurain_services import fetch_user_activities

        mock_request.return_value = self._json_response(
            {
                'items': [{'id': 1, 'name': 'Run'}],
                'total': 1,
                'page': 1,
                'num_records': 50,
                'next': None,
            }
        )
        integration = self._integration()

        activities = fetch_user_activities(
            integration,
            start_date='2026-10-25T00:00:00Z',
            end_date='2026-10-30',
            page_number=2,
            num_records=500,
        )

        self.assertEqual(activities, [{'id': 1, 'name': 'Run'}])
        mock_request.assert_called_once_with(
            integration,
            'GET',
            '/activities/users/7',
            params={
                'page_number': 2,
                'num_records': 200,
                'start_date': '2026-10-25',
                'end_date': '2026-10-30',
            },
        )

    @patch('integrations.endurain_services._request')
    def test_fetch_user_activities_treats_json_null_as_empty(self, mock_request):
        from integrations.endurain_services import fetch_user_activities

        mock_request.return_value = self._json_response(None)

        self.assertEqual(fetch_user_activities(self._integration()), [])
        mock_request.assert_called_once()

    @patch('integrations.endurain_services._request')
    def test_fetch_user_activities_falls_back_when_new_route_is_html(self, mock_request):
        from integrations.endurain_services import fetch_user_activities

        mock_request.side_effect = [
            self._html_response(),
            self._json_response([{'id': 3}]),
        ]

        activities = fetch_user_activities(self._integration(), page_number=1, num_records=50)

        self.assertEqual(activities, [{'id': 3}])
        self.assertEqual(
            mock_request.call_args_list[1].args[2],
            '/activities/user/7/page_number/1/num_records/50',
        )

    @patch('integrations.endurain_services._request')
    def test_fetch_user_activities_falls_back_when_new_route_is_missing(self, mock_request):
        from integrations.endurain_services import fetch_user_activities

        mock_request.side_effect = [
            self._json_response({'detail': 'Not Found'}, status_code=404),
            self._json_response({'records': [{'id': 4}]}),
        ]

        activities = fetch_user_activities(self._integration())

        self.assertEqual(activities, [{'id': 4}])
        self.assertEqual(mock_request.call_count, 2)

    @patch('integrations.endurain_services._request')
    def test_fetch_user_activities_uses_problem_detail_and_does_not_fall_back(self, mock_request):
        from integrations.endurain_services import fetch_user_activities

        mock_request.return_value = self._json_response(
            {
                'type': 'urn:endurain:error:invalid-input',
                'title': 'Invalid input',
                'status': 400,
                'detail': 'start_date is invalid',
            },
            status_code=400,
        )

        with self.assertRaises(IntegrationError) as ctx:
            fetch_user_activities(self._integration())

        self.assertEqual(ctx.exception.user_message, 'start_date is invalid')
        self.assertEqual(ctx.exception.code, 'endurain.fetch_failed')
        self.assertEqual(ctx.exception.status_code, 400)
        mock_request.assert_called_once()

    @patch('integrations.endurain_services._request')
    def test_fetch_user_activities_reads_problem_title_without_detail(self, mock_request):
        from integrations.endurain_services import fetch_user_activities

        mock_request.return_value = self._json_response(
            {'title': 'Invalid input', 'status': 422},
            status_code=422,
        )

        with self.assertRaises(IntegrationError) as ctx:
            fetch_user_activities(self._integration())

        self.assertEqual(ctx.exception.user_message, 'Invalid input')

    @patch('integrations.endurain_services._request')
    def test_fetch_user_activities_rejects_html_from_both_routes(self, mock_request):
        from integrations.endurain_services import fetch_user_activities

        mock_request.side_effect = [self._html_response(), self._html_response()]

        with self.assertRaises(IntegrationError) as ctx:
            fetch_user_activities(self._integration())

        self.assertEqual(ctx.exception.code, 'endurain.invalid_response')
        self.assertEqual(ctx.exception.status_code, 502)

    @patch('integrations.endurain_services._request')
    def test_validate_connection_accepts_activity_page(self, mock_request):
        from integrations.endurain_services import validate_connection

        mock_request.return_value = self._json_response(
            {'items': [], 'total': 0, 'page': 1, 'num_records': 1, 'next': None}
        )

        validate_connection(self._integration())

        self.assertEqual(mock_request.call_args.args[2], '/activities/users/7')
        self.assertEqual(mock_request.call_args.kwargs['params']['num_records'], 1)

    @patch('integrations.endurain_services._request')
    def test_validate_connection_rejects_html_success(self, mock_request):
        from integrations.endurain_services import validate_connection

        mock_request.side_effect = [self._html_response(), self._html_response()]

        with self.assertRaises(IntegrationError) as ctx:
            validate_connection(self._integration())

        self.assertEqual(ctx.exception.code, 'endurain.connection_failed')

    @patch('integrations.endurain_services._request')
    def test_validate_connection_maps_unauthorized_to_reconnect(self, mock_request):
        from integrations.endurain_services import validate_connection

        mock_request.return_value = self._json_response(
            {'title': 'Unauthorized', 'detail': 'Token expired', 'status': 401},
            status_code=401,
        )

        with self.assertRaises(IntegrationError) as ctx:
            validate_connection(self._integration())

        self.assertEqual(ctx.exception.code, 'endurain.reconnect_required')
        self.assertEqual(ctx.exception.status_code, 401)

    @patch('integrations.endurain_services._request')
    def test_fetch_activity_stream_uses_nested_route(self, mock_request):
        from integrations.endurain_services import _fetch_activity_stream

        mock_request.return_value = self._json_response(
            {'stream_type': 7, 'stream_waypoints': [{'lat': 1, 'lon': 2}]}
        )

        stream = _fetch_activity_stream(self._integration(), 11, 7)

        self.assertEqual(stream['stream_type'], 7)
        mock_request.assert_called_once_with(
            mock_request.call_args.args[0],
            'GET',
            '/activities/11/streams/7',
        )

    @patch('integrations.endurain_services._request')
    def test_fetch_activity_stream_falls_back_to_legacy_route(self, mock_request):
        from integrations.endurain_services import _fetch_activity_stream

        mock_request.side_effect = [
            self._html_response(),
            self._json_response({'stream_waypoints': [{'lat': 1, 'lon': 2}]}),
        ]

        stream = _fetch_activity_stream(self._integration(), 11, 7)

        self.assertEqual(len(stream['stream_waypoints']), 1)
        self.assertEqual(
            mock_request.call_args_list[1].args[2],
            '/activities_streams/activity_id/11/stream_type/7',
        )
