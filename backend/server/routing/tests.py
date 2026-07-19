"""Tests for the routing app: the pure optimize_order algorithm and the OSRM
HTTP client, both in isolation (no Django models involved — see
adventures/tests.py for the endpoint-level tests that exercise these
together against real itinerary data).
"""
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings

from routing.exceptions import OSRMUnavailableError
from routing.optimizer import _path_cost, optimize_order
from routing.osrm_client import OSRM_MAX_TABLE_SIZE, get_duration_matrix

# A symmetric matrix for 4 stops placed at the corners of a rectangle:
#   0 --10-- 1
#   |        |
#   14       14
#   |        |
#   3 --10-- 2
# The perimeter tour (either direction) costs 10+14+10+14=48 as a *cycle*,
# but optimize_order returns an open path, so the cheapest path visiting all
# 4 corners without closing the loop is one long side + two short sides:
# e.g. 0->1->2->3 costs 10+10+14=34 or 0->3->2->1 costs 14+10+10=34.
SQUARE_MATRIX = [
    [0, 10, 24, 14],
    [10, 0, 14, 24],
    [24, 14, 0, 10],
    [14, 24, 10, 0],
]


class OptimizeOrderTests(TestCase):
    def test_returns_valid_permutation_for_square(self):
        order = optimize_order(SQUARE_MATRIX)
        self.assertEqual(len(order), 4)
        self.assertEqual(set(order), {0, 1, 2, 3})

    def test_finds_the_known_optimal_path_for_square(self):
        order = optimize_order(SQUARE_MATRIX)
        # Optimal open-path cost visiting all 4 corners is 34 (two adjacent
        # sides + one short diagonal-free side); the naive input order
        # 0,1,2,3 already happens to be optimal here, but a shuffled input
        # matrix (see test below) proves the algorithm actually searches.
        self.assertEqual(_path_cost(SQUARE_MATRIX, order), 34)

    def test_finds_optimum_regardless_of_stop_index_order(self):
        # Same square, but row/column order shuffled so the identity order
        # is no longer optimal. Confirms 2-opt actually improves on the
        # nearest-neighbor seed rather than just echoing the input index order.
        # Shuffled mapping: new index -> old index: [2, 0, 3, 1]
        shuffled = [
            [SQUARE_MATRIX[oi][oj] for oj in (2, 0, 3, 1)] for oi in (2, 0, 3, 1)
        ]
        order = optimize_order(shuffled)
        self.assertEqual(set(order), {0, 1, 2, 3})
        self.assertEqual(_path_cost(shuffled, order), 34)

    def test_fixed_start_is_preserved(self):
        order = optimize_order(SQUARE_MATRIX, fixed_start=2)
        self.assertEqual(order[0], 2)
        self.assertEqual(set(order), {0, 1, 2, 3})

    def test_fixed_start_and_end_are_preserved(self):
        order = optimize_order(SQUARE_MATRIX, fixed_start=1, fixed_end=3)
        self.assertEqual(order[0], 1)
        self.assertEqual(order[-1], 3)
        self.assertEqual(set(order), {0, 1, 2, 3})

    def test_fixed_start_equals_fixed_end_raises(self):
        with self.assertRaises(ValueError):
            optimize_order(SQUARE_MATRIX, fixed_start=0, fixed_end=0)

    def test_degenerate_zero_stops(self):
        self.assertEqual(optimize_order([]), [])

    def test_degenerate_single_stop(self):
        self.assertEqual(optimize_order([[0]]), [0])

    def test_degenerate_two_stops_returns_identity(self):
        matrix = [[0, 5], [7, 0]]
        self.assertEqual(optimize_order(matrix), [0, 1])

    def test_asymmetric_matrix_uses_directed_costs(self):
        # 0->1 and 1->2 are cheap; every reverse direction is expensive.
        # The only good open path is 0->1->2 (cost 2); anything that
        # traverses an expensive directed edge costs at least 100.
        matrix = [
            [0, 1, 100],
            [100, 0, 1],
            [1, 100, 0],
        ]
        order = optimize_order(matrix)
        self.assertEqual(_path_cost(matrix, order), 2)
        self.assertEqual(order, [0, 1, 2])


class OSRMClientTests(TestCase):
    @override_settings()
    def test_missing_osrm_url_raises_unavailable(self):
        with patch.dict("os.environ", {"OSRM_URL": ""}, clear=False):
            with self.assertRaises(OSRMUnavailableError):
                get_duration_matrix([(0.0, 0.0), (1.0, 1.0)])

    def test_too_many_coordinates_raises_unavailable(self):
        coords = [(float(i), float(i)) for i in range(OSRM_MAX_TABLE_SIZE + 1)]
        with patch.dict("os.environ", {"OSRM_URL": "http://osrm:5000"}, clear=False):
            with self.assertRaises(OSRMUnavailableError):
                get_duration_matrix(coords)

    def test_single_coordinate_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_duration_matrix([(0.0, 0.0)])

    @patch("routing.osrm_client.requests.get")
    def test_successful_call_returns_matrix(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": "Ok",
            "durations": [[0, 120], [130, 0]],
        }
        mock_get.return_value = mock_response

        with patch.dict("os.environ", {"OSRM_URL": "http://osrm:5000"}, clear=False):
            matrix = get_duration_matrix([(41.9, 12.5), (45.4, 9.2)])

        self.assertEqual(matrix, [[0, 120], [130, 0]])
        called_url = mock_get.call_args.args[0]
        # OSRM expects lon,lat (reversed from this function's lat,lon input).
        self.assertIn("12.500000,41.900000", called_url)
        self.assertIn("9.200000,45.400000", called_url)

    @patch("routing.osrm_client.requests.get")
    def test_connection_error_raises_unavailable(self, mock_get):
        import requests

        mock_get.side_effect = requests.ConnectionError("boom")
        with patch.dict("os.environ", {"OSRM_URL": "http://osrm:5000"}, clear=False):
            with self.assertRaises(OSRMUnavailableError):
                get_duration_matrix([(0.0, 0.0), (1.0, 1.0)])

    @patch("routing.osrm_client.requests.get")
    def test_non_ok_osrm_code_raises_unavailable(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": "NoRoute", "message": "no route found"}
        mock_get.return_value = mock_response

        with patch.dict("os.environ", {"OSRM_URL": "http://osrm:5000"}, clear=False):
            with self.assertRaises(OSRMUnavailableError):
                get_duration_matrix([(0.0, 0.0), (1.0, 1.0)])

    @patch("routing.osrm_client.requests.get")
    def test_non_200_status_raises_unavailable(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        with patch.dict("os.environ", {"OSRM_URL": "http://osrm:5000"}, clear=False):
            with self.assertRaises(OSRMUnavailableError):
                get_duration_matrix([(0.0, 0.0), (1.0, 1.0)])
