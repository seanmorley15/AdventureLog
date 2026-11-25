"""Visits saved inside a location name the person saving them, like POST /api/visits/ does."""
from adventures.models import Location, Notification, Visit
from adventures.tests.base import AudienceTestBase


class NestedVisitTravelerTests(AudienceTestBase):
    def test_an_editor_adding_a_visit_through_the_location_is_its_traveler(self):
        kept = Visit.objects.create(location=self.hut, start_date='2026-05-01T00:00:00Z')
        kept.travelers.set([self.owner])
        self.as_user(self.editor)
        response = self.client.patch(
            f'/api/locations/{self.hut.id}/',
            {'visits': [{'id': str(kept.id), 'start_date': '2026-05-01T00:00:00Z'},
                        {'start_date': '2026-06-01T00:00:00Z'}]},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        new = Visit.objects.filter(location=self.hut).exclude(pk=kept.pk).get()
        self.assertEqual(list(new.travelers.values_list('username', flat=True)), ['editor'])
        self.assertEqual(list(kept.travelers.values_list('username', flat=True)), ['owner'])
        self.assertFalse(Notification.objects.exists())

    def test_the_owner_creating_a_location_with_visits_is_their_traveler(self):
        self.as_user(self.owner)
        response = self.client.post(
            '/api/locations/', {'name': 'Pier', 'visits': [{'start_date': '2026-06-01T00:00:00Z'}]}, format='json'
        )
        self.assertEqual(response.status_code, 201, response.content)
        visit = Location.objects.get(pk=response.data['id']).visits.get()
        self.assertEqual(list(visit.travelers.values_list('username', flat=True)), ['owner'])
