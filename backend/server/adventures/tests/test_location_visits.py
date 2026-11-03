from rest_framework.test import APITestCase

from adventures.models import Location, Visit
from users.models import CustomUser


class LocationNestedVisitUpdateTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='visit-user',
            email='visit-user@example.com',
            password='testpassword123',
        )
        self.client.force_authenticate(user=self.user)
        self.location = Location.objects.create(user=self.user, name='Acadia')
        Visit.objects.create(location=self.location, notes='first trip')

    def test_patch_with_visits_from_get_response(self):
        """Visits echoed back from a GET include `location`, which must not cause a 500."""
        url = f'/api/locations/{self.location.id}/'
        visits = self.client.get(url).json()['visits']
        self.assertEqual(visits[0]['location'], str(self.location.id))
        visits[0]['notes'] = 'second trip'

        response = self.client.patch(url, {'visits': visits}, format='json')

        self.assertEqual(response.status_code, 200, response.content)
        visit = Visit.objects.get(location=self.location)
        self.assertEqual(visit.notes, 'second trip')
