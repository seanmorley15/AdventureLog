import datetime

from django.contrib.contenttypes.models import ContentType
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
    def test_changing_collection_dates_keeps_trip_context_items(self):
        self.collection.start_date = datetime.date(2026, 11, 2)
        self.collection.end_date = datetime.date(2026, 11, 5)
        self.collection.save()
        global_item = CollectionItineraryItem.objects.create(
            collection=self.collection,
            content_type=ContentType.objects.get_for_model(Location),
            object_id=self.location.id,
            is_global=True,
            order=0,
        )
        outside_item = CollectionItineraryItem.objects.create(
            collection=self.collection,
            content_type=ContentType.objects.get_for_model(Location),
            object_id=self.location.id,
            date=datetime.date(2026, 11, 5),
            order=1,
        )

        response = self.client.patch(
            f'/api/collections/{self.collection.id}/',
            {'start_date': '2026-11-02', 'end_date': '2026-11-04'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(CollectionItineraryItem.objects.filter(id=global_item.id).exists())
        self.assertFalse(CollectionItineraryItem.objects.filter(id=outside_item.id).exists())
