"""The traveler rules refuse with ``TravelerError`` codes, lock the visit they change, and never import DRF."""
import inspect

from django.db import connection
from django.test.utils import CaptureQueriesContext

from adventures.models import Location, Visit
from adventures.services import travelers
from adventures.services.travelers import TravelerError
from adventures.tests.base import AudienceTestBase
from core.errors import ServiceError


class TravelerErrorTests(AudienceTestBase):
    def _visit(self, who):
        visit = Visit.objects.create(location=self.hut, start_date='2026-06-01T00:00:00Z')
        visit.travelers.set(who)
        return visit

    def test_service_does_not_import_drf(self):
        self.assertNotIn('rest_framework', inspect.getsource(travelers))

    def test_traveler_error_is_a_service_error(self):
        self.assertTrue(issubclass(TravelerError, ServiceError))

    def test_non_candidate_is_traveler_not_allowed(self):
        visit = self._visit([self.owner])
        with self.assertRaises(TravelerError) as ctx:
            travelers.set_travelers(visit, [self.stranger], self.editor)
        self.assertEqual((ctx.exception.code, ctx.exception.status), ('traveler_not_allowed', 400))
        self.as_user(self.editor)
        response = self.client.patch(
            f'/api/visits/{visit.id}/', {'traveler_uuids': [str(self.stranger.uuid)]}, format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 'traveler_not_allowed')

    def test_nobody_left_is_traveler_required(self):
        visit = self._visit([self.owner])
        with self.assertRaises(TravelerError) as ctx:
            travelers.set_travelers(visit, [], self.owner)
        self.assertEqual((ctx.exception.code, ctx.exception.status), ('traveler_required', 400))

    def test_add_to_trip_non_member_is_traveler_not_allowed(self):
        self.as_user(self.editor)
        response = self.client.post(
            f'/api/collections/{self.trip.id}/add-travelers/', {'user_uuids': [str(self.stranger.uuid)]},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 'traveler_not_allowed')

    def test_join_by_non_candidate_is_403(self):
        visit = self._visit([self.owner])
        with self.assertRaises(TravelerError) as ctx:
            travelers.join(visit, self.stranger)
        self.assertEqual(ctx.exception.status, 403)

    def test_take_my_visits_of_own_location(self):
        self.as_user(self.owner)
        response = self.client.post(f'/api/locations/{self.hut.id}/duplicate/', {'take_my_visits': True}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 'location_already_yours')

    def test_take_my_visits_without_visits_is_400_and_copies_nothing(self):
        self._visit([self.owner])
        before = Location.objects.count()
        self.as_user(self.editor)
        response = self.client.post(f'/api/locations/{self.hut.id}/duplicate/', {'take_my_visits': True}, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(response.data['code'], 'no_visits_to_take')
        self.assertEqual(Location.objects.count(), before)


class VisitLockTests(AudienceTestBase):
    def _visit(self, who):
        visit = Visit.objects.create(location=self.hut, start_date='2026-06-01T00:00:00Z')
        visit.travelers.set(who)
        return visit

    def _locks(self, call):
        with CaptureQueriesContext(connection) as queries:
            call()
        locks = [q['sql'] for q in queries if 'FOR UPDATE' in q['sql']]
        # Only the visit row: locking its location too would invert the order a location save takes.
        self.assertTrue(all('FOR UPDATE OF "adventures_visit"' in sql for sql in locks), locks)
        return locks

    def test_leave_join_and_delete_lock_the_visit(self):
        visit = self._visit([self.owner, self.editor])
        self.assertTrue(self._locks(lambda: travelers.leave(visit, self.editor)))
        self.assertTrue(self._locks(lambda: travelers.join(visit, self.viewer)))
        self.assertTrue(self._locks(lambda: travelers.remove_or_delete(visit, self.viewer)))

    def test_the_lenient_path_locks_the_visit_once(self):
        visit = self._visit([self.owner, self.editor])
        self.assertEqual(len(self._locks(lambda: travelers.detach_if_traveler(visit, self.editor))), 1)
        self.assertEqual(len(self._locks(lambda: travelers.remove_or_delete(visit, self.owner))), 1)

    def test_join_a_visit_deleted_meanwhile_is_404_not_a_database_error(self):
        visit = self._visit([self.editor])
        Visit.objects.filter(pk=visit.pk).delete()
        with self.assertRaises(TravelerError) as ctx:
            travelers.join(visit, self.viewer)
        self.assertEqual(ctx.exception.status, 404)

    def test_leave_reads_the_travelers_after_the_lock(self):
        # Another request took the owner off since this instance was loaded: leaving now empties it.
        visit = self._visit([self.owner, self.editor])
        stale = Visit.objects.get(pk=visit.pk)
        list(stale.travelers.all())  # loaded before the change
        Visit.objects.get(pk=visit.pk).travelers.remove(self.owner)
        self.assertTrue(travelers.leave(stale, self.editor))
        self.assertFalse(Visit.objects.filter(pk=visit.pk).exists())
