from django.utils import timezone
from rest_framework.test import APITestCase

from adventures.models import Transportation
from users.models import CustomUser


class TransportationMotorcycleAPITests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='motorcycle-user',
            email='motorcycle-user@example.com',
            password='testpassword123',
        )
        self.client.force_authenticate(user=self.user)

    def test_motorcycle_can_be_created_and_retrieved(self):
        create_response = self.client.post(
            '/api/transportations/',
            {'name': 'Mountain motorcycle tour', 'type': 'motorcycle'},
            format='json',
        )

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.json()['type'], 'motorcycle')

        transportation_id = create_response.json()['id']
        retrieve_response = self.client.get(f'/api/transportations/{transportation_id}/')

        self.assertEqual(retrieve_response.status_code, 200)
        self.assertEqual(retrieve_response.json()['type'], 'motorcycle')

    def test_motorcycle_type_persists_when_editing_other_fields(self):
        create_response = self.client.post(
            '/api/transportations/',
            {'name': 'Original ride', 'type': 'motorcycle'},
            format='json',
        )
        self.assertEqual(create_response.status_code, 201)
        transportation_id = create_response.json()['id']

        update_response = self.client.patch(
            f'/api/transportations/{transportation_id}/',
            {'name': 'Updated ride'},
            format='json',
        )

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()['name'], 'Updated ride')
        self.assertEqual(update_response.json()['type'], 'motorcycle')

    def test_motorcycle_calendar_event_uses_motorcycle_icon(self):
        transportation = Transportation.objects.create(
            user=self.user,
            name='Calendar ride',
            type='motorcycle',
            date=timezone.now(),
        )

        response = self.client.get('/api/calendar/events/?types=transportation')

        self.assertEqual(response.status_code, 200)
        event = next(
            item
            for item in response.json()['events']
            if item['resource_id'] == str(transportation.id)
        )
        self.assertEqual(event['icon'], '🏍️')
