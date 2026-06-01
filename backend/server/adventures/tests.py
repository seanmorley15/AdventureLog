from rest_framework.test import APITestCase

from adventures.models import Collection, CollectionItineraryItem, Location
from users.models import CustomUser


class ItineraryAPITestCase(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='itinerary-user',
            email='itinerary-user@example.com',
            password='testpassword123',
        )
        self.collection = Collection.objects.create(user=self.user, name='Test Trip')
        self.location = Location.objects.create(user=self.user, name='Test Location', is_public=True)
        self.client.force_authenticate(user=self.user)

    def test_create_global_itinerary_item_without_date(self):
        response = self.client.post(
            '/api/itineraries/',
            {
                'collection': str(self.collection.id),
                'content_type': 'location',
                'object_id': str(self.location.id),
                'is_global': True,
                'order': 0,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(CollectionItineraryItem.objects.count(), 1)

        item = CollectionItineraryItem.objects.get()
        self.assertTrue(item.is_global)
        self.assertIsNone(item.date)
        self.assertEqual(item.collection, self.collection)

        payload = response.json()
        self.assertTrue(payload['is_global'])
        self.assertIsNone(payload['date'])

    def test_create_dated_itinerary_item_without_date_is_rejected(self):
        response = self.client.post(
            '/api/itineraries/',
            {
                'collection': str(self.collection.id),
                'content_type': 'location',
                'object_id': str(self.location.id),
                'is_global': False,
                'order': 0,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['date'][0], 'Dated items must include a date. To create a trip-wide item, set is_global=true.')
