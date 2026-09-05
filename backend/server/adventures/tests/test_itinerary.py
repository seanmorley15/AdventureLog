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
        self.assertEqual(payload['content_type'], 'location')
        self.assertEqual(payload['object_name'], 'location')
        self.assertEqual(payload['item']['type'], 'location')

    def test_collection_retrieve_serializes_itinerary_content_type_as_model_name(self):
        self.collection.locations.add(self.location)
        create_response = self.client.post(
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
        self.assertEqual(create_response.status_code, 201)

        response = self.client.get(f'/api/collections/{self.collection.id}/')
        self.assertEqual(response.status_code, 200)

        itinerary = response.json()['itinerary']
        self.assertEqual(len(itinerary), 1)
        self.assertEqual(itinerary[0]['content_type'], 'location')
        self.assertEqual(itinerary[0]['object_name'], 'location')
        self.assertEqual(itinerary[0]['object_id'], str(self.location.id))