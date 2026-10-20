from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from adventures.models import Activity, Location, Visit
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
