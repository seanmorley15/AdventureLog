from unittest.mock import patch

from rest_framework.test import APITestCase

from core.testing import make_user

SEARCH = 'adventures.views.recommendations.search_places'
RECO = 'adventures.views.recommendations.get_recommendations'
EMPTY = {'count': 0, 'category': 'food', 'results': [], 'sources_used': {'google': 0, 'osm': 0, 'merged': 0},
         'warnings': []}


class RecommendationsViewTests(APITestCase):
    def setUp(self):
        self.client.force_authenticate(make_user('rec-user', password='pw-12345678'))

    def get(self, **params):
        return self.client.get('/api/recommendations/', params)

    @patch(RECO, return_value=EMPTY)
    def test_coordinates_and_defaults(self, reco):
        response = self.get(lat=1, lon=2, category='food')
        self.assertEqual(response.status_code, 200)
        kwargs = reco.call_args.kwargs
        self.assertEqual((kwargs['lat'], kwargs['lon'], kwargs['limit'], kwargs['sources']), (1.0, 2.0, 30, 'both'))

    def test_validation(self):
        self.assertEqual(self.get(category='food').status_code, 400)
        self.assertEqual(self.get(lat=1, lon=2, category='bogus').status_code, 400)
        self.assertEqual(self.get(lat=1, lon=2, category='food', limit=500).status_code, 400)

    @patch(RECO, return_value=EMPTY)
    def test_legacy_tourism_category_is_accepted(self, reco):
        self.assertEqual(self.get(lat=1, lon=2, category='tourism').status_code, 200)
        self.assertEqual(reco.call_args.kwargs['category'], 'tourism')

    @patch(RECO, return_value=EMPTY)
    @patch(SEARCH)
    def test_location_lookup_accepts_zero_coordinates(self, search, reco):
        search.return_value.error = None
        search.return_value.results = [{'lat': '0.0', 'lon': '0.0'}]
        self.assertEqual(self.get(location='Null Island', category='food').status_code, 200)
        self.assertEqual((reco.call_args.kwargs['lat'], reco.call_args.kwargs['lon']), (0.0, 0.0))

    @patch(RECO)
    @patch(SEARCH)
    def test_location_not_found(self, search, reco):
        search.return_value.error = None
        search.return_value.results = []
        response = self.get(location='Nowhere', category='food')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'location_not_found')
        reco.assert_not_called()

    @patch(RECO)
    def test_service_error_becomes_503(self, reco):
        from core.errors import ServiceError

        reco.side_effect = ServiceError('down', code='upstream_error', status=503)
        response = self.get(lat=1, lon=2, category='food')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['code'], 'upstream_error')
