"""Phase 3: type conversion keeps days, and collection-created places belong to the owner."""

from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APITestCase

from adventures.models import Collection, CollectionItineraryDay, CollectionItineraryItem, Location
from adventures.utils.geo import make_point
from users.models import CustomUser


class WorkspaceTests(APITestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='workspace-owner', email='workspace-owner@example.com', password='testpassword123'
        )
        self.collaborator = CustomUser.objects.create_user(
            username='workspace-collab', email='workspace-collab@example.com', password='testpassword123'
        )
        self.client.force_authenticate(user=self.owner)

    def test_trip_to_folder_hides_days_without_deleting_them(self):
        trip = Collection.objects.create(user=self.owner, name='Week', type='trip')
        CollectionItineraryDay.objects.create(collection=trip, index=1)
        CollectionItineraryDay.objects.create(collection=trip, index=2)

        response = self.client.patch(f'/api/collections/{trip.id}/', {'type': 'folder'}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['type'], 'folder')
        self.assertEqual(CollectionItineraryDay.objects.filter(collection=trip, index__isnull=False).count(), 2)

    def test_folder_to_trip_shows_saved_days_and_does_not_duplicate_them(self):
        folder = Collection.objects.create(user=self.owner, name='Saved', type='folder')
        CollectionItineraryDay.objects.create(collection=folder, index=1)
        museum = Location.objects.create(user=self.owner, name='Museum')
        museum.collections.add(folder)
        location_ct = ContentType.objects.get_for_model(Location)
        CollectionItineraryItem.objects.create(
            collection=folder,
            content_type=location_ct,
            object_id=museum.id,
            day=folder.itinerary_days.get(index=1),
            order=0,
        )

        response = self.client.patch(f'/api/collections/{folder.id}/', {'type': 'trip'}, format='json')

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(CollectionItineraryDay.objects.filter(collection=folder).count(), 1)
        self.assertEqual(
            CollectionItineraryItem.objects.filter(collection=folder, object_id=museum.id).count(),
            1,
        )

        again = self.client.patch(f'/api/collections/{folder.id}/', {'type': 'folder'}, format='json')
        self.assertEqual(again.status_code, 200)
        back = self.client.patch(f'/api/collections/{folder.id}/', {'type': 'trip'}, format='json')
        self.assertEqual(back.status_code, 200)
        self.assertEqual(
            CollectionItineraryItem.objects.filter(collection=folder, object_id=museum.id).count(),
            1,
        )

    def test_folder_to_trip_with_no_days_lands_locations_in_ideas(self):
        folder = Collection.objects.create(user=self.owner, name='List', type='folder')
        museum = Location.objects.create(user=self.owner, name='Museum')
        cafe = Location.objects.create(user=self.owner, name='Cafe')
        museum.collections.add(folder)
        cafe.collections.add(folder)

        response = self.client.patch(f'/api/collections/{folder.id}/', {'type': 'trip'}, format='json')

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(CollectionItineraryDay.objects.filter(collection=folder).count(), 0)
        items = CollectionItineraryItem.objects.filter(collection=folder)
        self.assertEqual(items.count(), 2)
        self.assertTrue(all(item.day_id is None and item.is_global is False and item.date is None for item in items))

        again = self.client.patch(f'/api/collections/{folder.id}/', {'type': 'folder'}, format='json')
        self.assertEqual(again.status_code, 200)
        back = self.client.patch(f'/api/collections/{folder.id}/', {'type': 'trip'}, format='json')
        self.assertEqual(back.status_code, 200)
        self.assertEqual(CollectionItineraryItem.objects.filter(collection=folder).count(), 2)

    def test_collaborator_created_place_is_owned_by_the_collection_owner(self):
        trip = Collection.objects.create(user=self.owner, name='Shared', type='trip')
        trip.shared_with.add(self.collaborator)
        self.client.force_authenticate(user=self.collaborator)

        response = self.client.post(
            '/api/locations/',
            {'name': 'Shared cafe', 'collections': [str(trip.id)], 'latitude': 45.5, 'longitude': -73.5},
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.content)
        location = Location.objects.get(name='Shared cafe')
        self.assertEqual(location.user_id, self.owner.id)
        self.assertTrue(location.collections.filter(id=trip.id).exists())

        pins = self.client.get('/api/locations/pins/')
        self.assertEqual(pins.status_code, 200)
        self.assertNotIn(str(location.id), [row['id'] for row in pins.json()])

    def test_suggest_returns_places_near_the_collection_and_name_search(self):
        trip = Collection.objects.create(user=self.owner, name='Montreal', type='trip')
        here = Location.objects.create(user=self.owner, name='Old Port', coordinates=make_point(-73.55, 45.51))
        here.collections.add(trip)
        nearby = Location.objects.create(user=self.owner, name='Mount Royal', coordinates=make_point(-73.59, 45.50))
        far = Location.objects.create(user=self.owner, name='Pikes Peak', coordinates=make_point(-105.04, 38.84))

        near = self.client.get('/api/locations/suggest/', {'collection': str(trip.id)})
        self.assertEqual(near.status_code, 200, near.content)
        body = near.json()
        self.assertTrue(body['anchored'])
        self.assertEqual([row['id'] for row in body['results'][:2]], [str(here.id), str(nearby.id)])
        self.assertNotIn(str(far.id), [row['id'] for row in body['results'][:2]] if len(body['results']) > 2 else [])
        # nearest two are the Montreal places; the far one is last if included
        self.assertEqual(body['results'][-1]['id'], str(far.id))

        found = self.client.get('/api/locations/suggest/', {'collection': str(trip.id), 'q': 'Pikes'})
        self.assertEqual(found.status_code, 200)
        self.assertEqual([row['name'] for row in found.json()['results']], ['Pikes Peak'])

        empty = self.client.get('/api/locations/suggest/')
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.json()['results'], [])
        self.assertFalse(empty.json()['anchored'])
