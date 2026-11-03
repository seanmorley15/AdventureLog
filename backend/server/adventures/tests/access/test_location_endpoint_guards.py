from rest_framework.test import APITestCase


class LocationEndpointGuardTests(APITestCase):
    def test_the_list_answers_anonymous_requests_with_401(self):
        response = self.client.get('/api/locations/')

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['code'], 'not_authenticated')
