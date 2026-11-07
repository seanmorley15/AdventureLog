from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.db import IntegrityError
from django.utils import timezone
from rest_framework.test import APITestCase

from adventures.models import Activity, Category, Collection, Location, Visit
from users.models import CustomUser


class LocationVisitSyncTests(APITestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='visit-owner', email='visit-owner@example.com', password='testpassword123'
        )
        self.location = Location.objects.create(user=self.owner, name='Ridge')
        now = timezone.now()
        self.first = Visit.objects.create(
            location=self.location, start_date=now - timedelta(days=10), end_date=now - timedelta(days=9), notes='first'
        )
        self.second = Visit.objects.create(
            location=self.location, start_date=now - timedelta(days=5), end_date=now - timedelta(days=4), notes='second'
        )
        self.hike = Activity.objects.create(user=self.owner, visit=self.first, name='Ridge walk')
        self.url = f'/api/locations/{self.location.id}/'
        self.client.force_authenticate(user=self.owner)

    def _visit_payload(self, visit, **changes):
        return {
            'id': str(visit.id),
            'start_date': visit.start_date.isoformat(),
            'end_date': visit.end_date.isoformat(),
            'notes': visit.notes,
            **changes,
        }

    def test_visits_sent_back_with_ids_are_kept_with_their_activities(self):
        response = self.client.patch(
            self.url, {'visits': [self._visit_payload(self.first, notes='edited')]}, format='json'
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.first.refresh_from_db()
        self.assertEqual(self.first.notes, 'edited')
        self.assertTrue(Activity.objects.filter(pk=self.hike.pk, visit=self.first).exists())
        self.assertFalse(Visit.objects.filter(pk=self.second.pk).exists())
        self.assertEqual(self.location.visits.count(), 1)
        self.assertEqual([v['id'] for v in response.json()['visits']], [str(self.first.id)])

    def test_visit_without_an_id_is_created(self):
        new_start = timezone.now() + timedelta(days=3)
        response = self.client.patch(
            self.url,
            {
                'visits': [
                    self._visit_payload(self.first),
                    self._visit_payload(self.second),
                    {'start_date': new_start.isoformat(), 'end_date': new_start.isoformat(), 'notes': 'planned'},
                ]
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.location.visits.count(), 3)
        self.assertTrue(self.location.visits.filter(notes='planned').exists())
        self.assertTrue(Visit.objects.filter(pk=self.first.pk).exists())
        self.assertTrue(Visit.objects.filter(pk=self.second.pk).exists())

    def test_clients_that_send_no_ids_still_replace_the_list(self):
        new_start = timezone.now() + timedelta(days=3)
        response = self.client.patch(
            self.url,
            {'visits': [{'start_date': new_start.isoformat(), 'end_date': new_start.isoformat(), 'notes': 'only'}]},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(list(self.location.visits.values_list('notes', flat=True)), ['only'])

    def test_an_empty_list_removes_every_visit_and_their_activities(self):
        response = self.client.patch(self.url, {'visits': []}, format='json')

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.location.visits.count(), 0)
        self.assertFalse(Activity.objects.filter(pk=self.hike.pk).exists())

    def test_omitting_visits_leaves_them_alone(self):
        response = self.client.patch(self.url, {'name': 'Ridge, renamed'}, format='json')

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.location.visits.count(), 2)

    def test_an_id_from_another_place_is_not_adopted(self):
        other = Location.objects.create(user=self.owner, name='Elsewhere')
        now = timezone.now()
        foreign = Visit.objects.create(location=other, start_date=now, end_date=now, notes='not yours')

        response = self.client.patch(
            self.url,
            {'visits': [self._visit_payload(foreign, notes='hijacked')]},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        foreign.refresh_from_db()
        self.assertEqual(foreign.location, other)
        self.assertEqual(foreign.notes, 'not yours')
        self.assertEqual(list(self.location.visits.values_list('notes', flat=True)), ['hijacked'])


class LocationVisitCreateTests(APITestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='create-visit-owner', email='create-visit-owner@example.com', password='testpassword123'
        )
        self.collection = Collection.objects.create(user=self.owner, name='Madrid trip')
        self.client.force_authenticate(user=self.owner)
        self.visit_data = {
            'start_date': '2025-11-13T09:00:00+01:00',
            'end_date': '2025-11-13T17:00:00+01:00',
            'timezone': 'Europe/Madrid',
            'notes': 'First visit',
        }

    def test_creates_location_and_visits_in_one_request(self):
        response = self.client.post(
            '/api/locations/',
            {
                'name': 'Museum',
                'latitude': 40.4,
                'longitude': -3.7,
                'category': {'name': 'museum', 'display_name': 'Museums', 'icon': 'M'},
                'collections': [str(self.collection.id)],
                'visits': [self.visit_data, {**self.visit_data, 'notes': 'Return visit'}],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.content)
        location = Location.objects.get(pk=response.json()['id'])
        self.assertEqual(location.user, self.owner)
        self.assertEqual(location.category.name, 'museum')
        self.assertEqual(list(location.collections.all()), [self.collection])
        self.assertEqual((location.coordinates.y, location.coordinates.x), (40.4, -3.7))
        self.assertEqual(location.visits.count(), 2)
        self.assertEqual(set(location.visits.values_list('notes', flat=True)), {'First visit', 'Return visit'})
        for visit in response.json()['visits']:
            self.assertEqual(visit['location'], str(location.id))
            self.assertEqual(visit['timezone'], 'Europe/Madrid')
            self.assertEqual(visit['start_date'], '2025-11-13T08:00:00Z')
            self.assertEqual(visit['end_date'], '2025-11-13T16:00:00Z')
        detail = self.client.get(f'/api/locations/{location.id}/')
        self.assertEqual(detail.status_code, 200, detail.content)
        self.assertEqual(detail.json()['visits'], response.json()['visits'])

    def test_accepts_an_empty_visit_list(self):
        response = self.client.post('/api/locations/', {'name': 'Unvisited', 'visits': []}, format='json')

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['visits'], [])
        self.assertFalse(Visit.objects.exists())

    def test_retrying_a_location_id_does_not_duplicate_its_visits(self):
        payload = {'id': str(uuid4()), 'name': 'Offline place', 'visits': [self.visit_data]}
        created = self.client.post('/api/locations/', payload, format='json')
        self.assertEqual(created.status_code, 201, created.content)

        retried = self.client.post('/api/locations/', payload, format='json')

        self.assertEqual(retried.status_code, 200, retried.content)
        self.assertEqual(retried.json()['id'], payload['id'])
        self.assertEqual(retried.json()['visits'], created.json()['visits'])
        self.assertEqual(Location.objects.count(), 1)
        self.assertEqual(Visit.objects.count(), 1)

    def test_accepts_a_location_without_visits(self):
        response = self.client.post('/api/locations/', {'name': 'Unvisited'}, format='json')

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['visits'], [])

    def test_nested_visits_belong_to_the_new_location_even_when_copied(self):
        other_user = CustomUser.objects.create_user(username='other-visit-owner')
        other_location = Location.objects.create(user=other_user, name='Another place')
        other_visit = Visit.objects.create(location=other_location, **self.visit_data)

        response = self.client.post(
            '/api/locations/',
            {
                'name': 'New place',
                'visits': [{**self.visit_data, 'id': str(other_visit.id), 'location': str(other_location.id)}],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.content)
        new_visit = response.json()['visits'][0]
        self.assertNotEqual(new_visit['id'], str(other_visit.id))
        self.assertEqual(new_visit['location'], response.json()['id'])
        other_visit.refresh_from_db()
        self.assertEqual(other_visit.location, other_location)
        self.assertEqual(other_visit.notes, 'First visit')
        self.assertEqual(other_location.visits.count(), 1)

    def test_invalid_nested_visit_leaves_no_location_or_category(self):
        response = self.client.post(
            '/api/locations/',
            {
                'name': 'Invalid place',
                'category': {'name': 'new-category', 'display_name': 'New category', 'icon': 'N'},
                'collections': [str(self.collection.id)],
                'visits': [self.visit_data, {**self.visit_data, 'start_date': 'not-a-date'}],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn('start_date', response.json()['fields']['visits'][1])
        self.assertFalse(Location.objects.exists())
        self.assertFalse(Visit.objects.exists())
        self.assertFalse(Category.objects.filter(name='new-category').exists())

    def test_visit_save_failure_rolls_back_the_whole_creation(self):
        original_save = Visit.save
        saved_visits = []

        def save_then_fail(visit, *args, **kwargs):
            if saved_visits:
                raise IntegrityError('second visit failed')
            original_save(visit, *args, **kwargs)
            saved_visits.append(visit.pk)

        with patch.object(Visit, 'save', autospec=True, side_effect=save_then_fail):
            response = self.client.post(
                '/api/locations/',
                {
                    'name': 'Unfinished place',
                    'category': {'name': 'new-category', 'display_name': 'New category', 'icon': 'N'},
                    'collections': [str(self.collection.id)],
                    'visits': [self.visit_data, {**self.visit_data, 'notes': 'Second'}],
                },
                format='json',
            )

        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(response.json()['code'], 'conflict')
        self.assertEqual(len(saved_visits), 1)
        self.assertFalse(Location.objects.exists())
        self.assertFalse(Visit.objects.exists())
        self.assertFalse(Category.objects.filter(name='new-category').exists())
        self.assertFalse(Location.collections.through.objects.exists())

    def test_standalone_visit_creation_still_requires_a_location(self):
        response = self.client.post('/api/visits/', self.visit_data, format='json')

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn('location', response.json()['fields'])
        self.assertFalse(Visit.objects.exists())

    def test_standalone_visit_creation_with_a_location_still_works(self):
        location = Location.objects.create(user=self.owner, name='Existing place')
        response = self.client.post(
            '/api/visits/', {**self.visit_data, 'location': str(location.id)}, format='json'
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['location'], str(location.id))
        self.assertEqual(location.visits.count(), 1)
