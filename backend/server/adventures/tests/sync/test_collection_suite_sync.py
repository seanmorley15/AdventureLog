"""Collections, stays and journeys take a client-chosen id and ``If-Match`` too, so a trip can be planned offline."""

import uuid

from rest_framework.test import APITestCase

from adventures.models import Collection, Lodging, Transportation
from core.testing import make_user


class CollectionSuiteSyncTests(APITestCase):
    def setUp(self):
        self.user = make_user('suite-owner')
        self.client.force_authenticate(user=self.user)

    def post(self, path, body):
        return self.client.post(path, body, format='json')

    def test_a_collection_keeps_the_id_the_client_chose_and_a_retry_makes_no_second(self):
        chosen = str(uuid.uuid4())
        first = self.post('/api/collections/', {'id': chosen, 'name': 'Norway'})
        retry = self.post('/api/collections/', {'id': chosen, 'name': 'Norway'})

        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(first.json()['id'], chosen)
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(Collection.objects.filter(user=self.user, name='Norway').count(), 1)

    def test_a_stay_and_a_journey_keep_their_ids(self):
        trip = Collection.objects.create(user=self.user, name='Norway')
        stay_id, ride_id = str(uuid.uuid4()), str(uuid.uuid4())

        stay = self.post('/api/lodgings/', {'id': stay_id, 'name': 'Hotel', 'collection': str(trip.id)})
        ride = self.post(
            '/api/transportations/', {'id': ride_id, 'name': 'Train', 'type': 'train', 'collection': str(trip.id)}
        )

        self.assertEqual(stay.status_code, 201, stay.content)
        self.assertEqual(ride.status_code, 201, ride.content)
        self.assertTrue(Lodging.objects.filter(pk=stay_id).exists())
        self.assertTrue(Transportation.objects.filter(pk=ride_id).exists())

    def test_a_stale_if_match_is_refused_for_each_kind(self):
        trip = Collection.objects.create(user=self.user, name='Norway')
        stay = Lodging.objects.create(user=self.user, name='Hotel', collection=trip)
        for path in (f'/api/collections/{trip.id}/', f'/api/lodgings/{stay.id}/'):
            response = self.client.patch(path, {'name': 'x'}, format='json', HTTP_IF_MATCH='"1"')
            self.assertEqual(response.status_code, 412, path)

    def test_a_current_if_match_lets_the_change_through(self):
        trip = Collection.objects.create(user=self.user, name='Norway')
        etag = self.client.get(f'/api/collections/{trip.id}/')['ETag']

        response = self.client.patch(
            f'/api/collections/{trip.id}/', {'name': 'Norway 2'}, format='json', HTTP_IF_MATCH=etag
        )

        self.assertEqual(response.status_code, 200, response.content)
        trip.refresh_from_db()
        self.assertEqual(trip.name, 'Norway 2')
