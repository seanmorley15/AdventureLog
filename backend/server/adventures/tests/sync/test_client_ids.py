"""
A client may choose the id of a record it creates. Retrying a create whose answer was lost then returns
the record that already exists instead of making a second one.
"""

import uuid

from rest_framework.test import APITestCase

from adventures.models import Checklist, Location, Note, Visit
from core.testing import make_user


class ClientIdTests(APITestCase):
    def setUp(self):
        self.user = make_user('ids-owner')
        self.client.force_authenticate(user=self.user)

    def create(self, path, body, **extra):
        return self.client.post(path, body, format='json', **extra)

    def test_a_location_is_created_with_the_id_the_client_chose(self):
        chosen = uuid.uuid4()

        response = self.create('/api/locations/', {'id': str(chosen), 'name': 'Reine'})

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['id'], str(chosen))
        self.assertTrue(Location.objects.filter(pk=chosen, user=self.user).exists())

    def test_without_an_id_the_server_picks_one_as_before(self):
        response = self.create('/api/locations/', {'name': 'Reine'})

        self.assertEqual(response.status_code, 201)
        uuid.UUID(response.json()['id'])

    def test_retrying_returns_the_same_record_and_makes_no_second_one(self):
        chosen = str(uuid.uuid4())
        first = self.create('/api/locations/', {'id': chosen, 'name': 'Reine'})

        retry = self.create('/api/locations/', {'id': chosen, 'name': 'Reine'})

        self.assertEqual(first.status_code, 201)
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry.json()['id'], chosen)
        self.assertEqual(Location.objects.filter(user=self.user, name='Reine').count(), 1)

    def test_a_retry_returns_the_stored_record_not_the_new_payload(self):
        chosen = str(uuid.uuid4())
        self.create('/api/locations/', {'id': chosen, 'name': 'Reine'})

        retry = self.create('/api/locations/', {'id': chosen, 'name': 'Changed my mind'})

        self.assertEqual(retry.json()['name'], 'Reine')

    def test_an_id_that_belongs_to_someone_elses_private_record_is_a_conflict(self):
        other = Location.objects.create(user=make_user('ids-other'), name='Private', is_public=False)

        response = self.create('/api/locations/', {'id': str(other.id), 'name': 'Mine'})

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'conflict')
        other.refresh_from_db()
        self.assertEqual(other.name, 'Private')

    def test_an_id_that_is_not_a_uuid_is_a_validation_error(self):
        response = self.create('/api/locations/', {'id': 'not-a-uuid', 'name': 'Reine'})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'validation_error')
        self.assertIn('id', response.json()['fields'])

    def test_a_retry_is_answered_even_when_the_payload_would_now_be_invalid(self):
        chosen = str(uuid.uuid4())
        self.create('/api/locations/', {'id': chosen, 'name': 'Reine'})

        retry = self.create('/api/locations/', {'id': chosen})

        self.assertEqual(retry.status_code, 200)

    def test_an_invalid_new_record_is_still_rejected(self):
        response = self.create('/api/locations/', {'id': str(uuid.uuid4())})

        self.assertEqual(response.status_code, 400)

    def test_a_retried_create_still_carries_the_etag(self):
        chosen = str(uuid.uuid4())
        self.create('/api/locations/', {'id': chosen, 'name': 'Reine'})

        retry = self.create('/api/locations/', {'id': chosen, 'name': 'Reine'})

        self.assertRegex(retry['ETag'], r'^"\d+"$')

    def test_visits_notes_and_checklists_accept_ids_too(self):
        place = Location.objects.create(user=self.user, name='Reine')
        cases = [
            ('/api/visits/', {'location': str(place.id), 'start_date': '2026-06-01T00:00:00Z'}, Visit),
            ('/api/notes/', {'name': 'Pack', 'content': 'x'}, Note),
            ('/api/checklists/', {'name': 'Gear', 'items': []}, Checklist),
        ]
        for path, body, model in cases:
            with self.subTest(path=path):
                chosen = str(uuid.uuid4())
                first = self.create(path, {**body, 'id': chosen})
                retry = self.create(path, {**body, 'id': chosen})
                self.assertEqual(first.status_code, 201, first.content)
                self.assertEqual(first.json()['id'], chosen)
                self.assertEqual(retry.status_code, 200)
                self.assertEqual(model.objects.filter(pk=chosen).count(), 1)

    def test_a_collaborator_retrying_a_create_in_a_shared_collection_gets_the_record(self):
        from adventures.models import Collection

        owner = make_user('ids-trip-owner')
        trip = Collection.objects.create(user=owner, name='Trip', type='trip')
        trip.shared_with.add(self.user)
        chosen = str(uuid.uuid4())
        body = {'id': chosen, 'name': 'Pack', 'content': 'x', 'collection': str(trip.id)}

        first = self.create('/api/notes/', body)
        retry = self.create('/api/notes/', body)

        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(Note.objects.get(pk=chosen).user, owner)
