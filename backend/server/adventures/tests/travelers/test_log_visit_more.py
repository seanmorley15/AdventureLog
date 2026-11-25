"""Log visit cases the first tests left out."""
from adventures.models import Notification, Visit
from adventures.tests.base import AudienceTestBase


class LogVisitMoreTests(AudienceTestBase):
    def _url(self):
        return f'/api/collections/{self.trip.id}/itinerary-items/{self.stop.id}/log-visit/'

    def _log(self, user, people):
        self.as_user(user)
        return self.client.post(self._url(), {'traveler_uuids': [str(p.uuid) for p in people]}, format='json')

    def test_a_viewer_cannot_log_a_visit(self):
        response = self._log(self.viewer, [self.viewer])
        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(Visit.objects.filter(location=self.hut).exists())

    def test_someone_added_by_an_actor_who_is_not_on_the_visit_is_told(self):
        visit = Visit.objects.create(location=self.hut, start_date='2026-06-01T00:00:00Z')
        visit.travelers.set([self.owner])
        self.stop.logged_visit = visit
        self.stop.save()
        response = self._log(self.editor, [self.viewer])
        self.assertEqual(response.status_code, 200, response.data)
        note = Notification.objects.get(user=self.viewer)
        self.assertEqual((note.actor_user, note.data['visit_id']), (self.editor, str(visit.id)))
        self.assertFalse(visit.travelers.filter(pk=self.editor.pk).exists())

    def test_an_existing_visit_on_the_same_dates_gains_the_list_without_the_actor(self):
        visit = Visit.objects.create(
            location=self.hut, start_date='2026-06-01T00:00:00Z', end_date='2026-06-01T23:59:59Z'
        )
        visit.travelers.set([self.owner])
        response = self._log(self.editor, [self.viewer])
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['visit']['id'], str(visit.id))
        self.assertEqual(sorted(visit.travelers.values_list('username', flat=True)), ['owner', 'viewer'])
        self.assertEqual(Visit.objects.filter(location=self.hut).count(), 1)
        self.assertTrue(Notification.objects.filter(user=self.viewer).exists())
