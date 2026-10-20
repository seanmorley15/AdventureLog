from rest_framework.test import APITestCase


class LocationEndpointGuardTests(APITestCase):
    def test_filtered_does_not_500_for_anonymous_requests(self):
        response = self.client.get('/api/locations/filtered/', {'types': 'all'})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'error': 'User is not authenticated'})
