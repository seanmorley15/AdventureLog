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

class ItineraryCreatePermissionTestCase(APITestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='itinerary-owner', email='itinerary-owner@example.com', password='testpassword123'
        )
        self.outsider = CustomUser.objects.create_user(
            username='itinerary-outsider', email='itinerary-outsider@example.com', password='testpassword123'
        )
        self.collection = Collection.objects.create(user=self.owner, name='Private Trip')
        self.location = Location.objects.create(user=self.owner, name='Owner Place')
        self.outsider_location = Location.objects.create(user=self.outsider, name='Outsider Place')

    def _payload(self, location, **extra):
        return {
            'collection': str(self.collection.id),
            'content_type': 'location',
            'object_id': str(location.id),
            'is_global': True,
            'order': 0,
            **extra,
        }

    def test_non_member_cannot_create_item_in_date_keyed_collection(self):
        self.client.force_authenticate(user=self.outsider)
        response = self.client.post('/api/itineraries/', self._payload(self.outsider_location), format='json')

        self.assertEqual(response.status_code, 403)
        self.assertEqual(CollectionItineraryItem.objects.count(), 0)

    def test_non_member_cannot_use_numeric_content_type_to_skip_object_check(self):
        from django.contrib.contenttypes.models import ContentType

        self.client.force_authenticate(user=self.outsider)
        payload = self._payload(self.outsider_location, content_type=ContentType.objects.get_for_model(Location).pk)
        response = self.client.post('/api/itineraries/', payload, format='json')

        self.assertEqual(response.status_code, 403)
        self.assertEqual(CollectionItineraryItem.objects.count(), 0)

    def test_owner_cannot_place_object_they_cannot_access_via_numeric_content_type(self):
        from django.contrib.contenttypes.models import ContentType

        self.client.force_authenticate(user=self.owner)
        payload = self._payload(self.outsider_location, content_type=ContentType.objects.get_for_model(Location).pk)
        response = self.client.post('/api/itineraries/', payload, format='json')

        self.assertEqual(response.status_code, 403)
        self.assertEqual(CollectionItineraryItem.objects.count(), 0)

    def test_owner_can_create_item_with_numeric_content_type(self):
        from django.contrib.contenttypes.models import ContentType

        self.client.force_authenticate(user=self.owner)
        payload = self._payload(self.location, content_type=ContentType.objects.get_for_model(Location).pk)
        response = self.client.post('/api/itineraries/', payload, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(CollectionItineraryItem.objects.count(), 1)
