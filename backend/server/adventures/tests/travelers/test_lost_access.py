"""A traveler who can no longer reach a location can take themselves off its visits, and read nothing else."""
from adventures.models import CollectionMember, Visit
from adventures.tests.base import AudienceTestBase


class LostAccessTravelerTests(AudienceTestBase):
    def setUp(self):
        super().setUp()
        self.visit = Visit.objects.create(location=self.hut, start_date='2026-06-01T00:00:00Z', notes='secret')
        self.visit.travelers.set([self.owner, self.editor])
        # Off the trip without being released (as data from before the release rules could be).
        self.trip.shared_with.remove(self.editor)
        CollectionMember.objects.filter(collection=self.trip, user=self.editor).delete()
        self.as_user(self.editor)

    def test_the_visits_list_leaves_it_out(self):
        response = self.client.get('/api/visits/')
        self.assertEqual(response.status_code, 200)
        rows = response.data['results'] if isinstance(response.data, dict) else response.data
        self.assertNotIn(str(self.visit.id), [row['id'] for row in rows])
        self.assertEqual(self.client.get(f'/api/visits/{self.visit.id}/').status_code, 404)

    def test_leave_answers_204_without_the_visit(self):
        response = self.client.post(f'/api/visits/{self.visit.id}/leave/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(list(self.visit.travelers.values_list('username', flat=True)), ['owner'])

    def test_a_member_leaving_still_gets_the_visit(self):
        self.visit.travelers.add(self.viewer)
        self.as_user(self.viewer)
        response = self.client.post(f'/api/visits/{self.visit.id}/leave/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['id'], str(self.visit.id))

    def test_the_owner_still_lists_the_visit(self):
        self.as_user(self.owner)
        response = self.client.get('/api/visits/')
        rows = response.data['results'] if isinstance(response.data, dict) else response.data
        self.assertIn(str(self.visit.id), [row['id'] for row in rows])
