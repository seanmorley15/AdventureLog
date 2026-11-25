"""The visits and notifications lists cost the same number of queries however many rows they hold."""
from django.db import connection
from django.test.utils import CaptureQueriesContext

from adventures.models import Location, Notification, Visit
from adventures.tests.base import AudienceTestBase


class ListQueryCountTests(AudienceTestBase):
    def _places(self, count):
        for n in range(count):
            place = Location.objects.create(user=self.owner, name=f'Extra {n}', is_public=False)
            place.collections.add(self.trip)
            visit = Visit.objects.create(location=place, start_date='2026-06-01T00:00:00Z')
            visit.travelers.set([self.owner, self.editor])

    def _queries(self, path):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(path)
        self.assertEqual(response.status_code, 200, response.content)
        return len(queries)

    def test_visits_list(self):
        self.as_user(self.editor)
        self._places(3)
        few = self._queries('/api/visits/')
        self._places(15)
        many = self._queries('/api/visits/')
        self.assertLessEqual(many, few, f'{few} queries for 3 visits, {many} for 18')

    def _notes(self, count):
        for n in range(count):
            place = Location.objects.create(user=self.owner, name=f'Note {n}', is_public=False)
            place.collections.add(self.trip)
            visit = Visit.objects.create(location=place, start_date='2026-06-01T00:00:00Z')
            Notification.objects.create(
                user=self.editor, kind=Notification.Kind.VISIT_TRAVELER_ADDED, actor_user=self.owner,
                actor_name='owner', data={
                    'count': 1, 'locations': 1, 'visit_id': str(visit.pk), 'location_id': str(place.pk),
                    'location_name': place.name, 'collection_id': str(self.trip.pk), 'collection_name': 'Lofoten',
                },
            )

    def test_notifications_list(self):
        self.as_user(self.editor)
        self._notes(3)
        few = self._queries('/api/notifications/')
        self._notes(15)
        many = self._queries('/api/notifications/')
        self.assertLessEqual(many, few, f'{few} queries for 3 notifications, {many} for 18')

    def test_suggest(self):
        self.as_user(self.owner)
        self._places(3)
        few = self._queries('/api/locations/suggest/')
        self._places(15)
        many = self._queries('/api/locations/suggest/')
        self.assertLessEqual(many, few, f'{few} queries for 4 places, {many} for 19')
