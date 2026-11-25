from adventures.models import Visit
from adventures.services import travelers
from adventures.services.travelers import TravelerError
from adventures.tests.base import AudienceTestBase


class DeleteSharedVisitTests(AudienceTestBase):
    def _visit(self, who):
        visit = Visit.objects.create(location=self.hut, start_date='2026-06-01T00:00:00Z')
        visit.travelers.set(who)
        return visit

    def _stop_url(self, query=''):
        return f'/api/collections/{self.trip.id}/itinerary-items/{self.stop.id}/{query}'

    def test_editor_delete_shared_visit_detaches(self):
        visit = self._visit([self.owner, self.editor])
        self.as_user(self.editor)
        response = self.client.delete(f'/api/visits/{visit.id}/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual([u.pk for u in visit.travelers.all()], [self.owner.pk])

    def test_owner_delete_for_everyone(self):
        visit = self._visit([self.owner, self.editor])
        self.as_user(self.owner)
        response = self.client.delete(f'/api/visits/{visit.id}/?for_everyone=1')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Visit.objects.filter(pk=visit.pk).exists())

    def test_editor_for_everyone_forbidden_403(self):
        visit = self._visit([self.owner, self.editor])
        self.as_user(self.editor)
        response = self.client.delete(f'/api/visits/{visit.id}/?for_everyone=1')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(visit.travelers.count(), 2)

    def test_delete_sole_traveler_deletes(self):
        visit = self._visit([self.editor])
        self.as_user(self.editor)
        self.assertEqual(self.client.delete(f'/api/visits/{visit.id}/').status_code, 204)
        self.assertFalse(Visit.objects.filter(pk=visit.pk).exists())

    def test_non_traveler_editor_delete_changes_nothing(self):
        visit = self._visit([self.owner])
        self.as_user(self.editor)
        self.assertEqual(self.client.delete(f'/api/visits/{visit.id}/').status_code, 204)
        self.assertEqual([u.pk for u in visit.travelers.all()], [self.owner.pk])
        self.assertEqual(travelers.remove_or_delete(visit, self.editor), 'detached')
        self.assertTrue(Visit.objects.filter(pk=visit.pk).exists())

    def test_detach_keeps_the_visit_activities(self):
        from adventures.models import Activity
        visit = self._visit([self.owner, self.editor])
        activity = Activity.objects.create(visit=visit, user=self.owner, name='Hike')
        self.as_user(self.editor)
        self.client.delete(f'/api/visits/{visit.id}/')
        self.assertTrue(Activity.objects.filter(pk=activity.pk).exists())

    def test_service_results(self):
        shared = self._visit([self.owner, self.editor])
        self.assertEqual(travelers.remove_or_delete(shared, self.editor), 'detached')
        self.assertEqual(travelers.remove_or_delete(shared, self.owner), 'deleted')
        again = self._visit([self.owner, self.editor])
        with self.assertRaises(TravelerError):
            travelers.remove_or_delete(again, self.editor, for_everyone=True)
        self.assertEqual(travelers.remove_or_delete(again, self.owner, for_everyone=True), 'deleted')

    def test_saving_location_without_shared_visit_detaches_only_editor(self):
        visit = self._visit([self.owner, self.editor])
        self.as_user(self.editor)
        response = self.client.patch(f'/api/locations/{self.hut.id}/', {'visits': []}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([u.pk for u in visit.travelers.all()], [self.owner.pk])

    def test_stop_delete_confirm_visits_detaches_when_shared(self):
        visit = self._visit([self.owner, self.editor])
        self.stop.logged_visit = visit
        self.stop.save()
        self.as_user(self.editor)
        response = self.client.delete(self._stop_url('?confirm_delete_visits=true'))
        self.assertEqual(response.status_code, 204, response.content)
        self.assertEqual([u.pk for u in visit.travelers.all()], [self.owner.pk])

    def test_stop_delete_confirm_visits_deletes_when_alone(self):
        visit = self._visit([self.editor])
        self.stop.logged_visit = visit
        self.stop.save()
        self.as_user(self.editor)
        self.assertEqual(self.client.delete(self._stop_url('?confirm_delete_visits=true')).status_code, 204)
        self.assertFalse(Visit.objects.filter(pk=visit.pk).exists())


class VisitWithNoTravelersTests(AudienceTestBase):
    def test_owner_delete_removes_a_visit_nobody_travelled_on(self):
        visit = Visit.objects.create(location=self.hut, start_date='2026-06-01T00:00:00Z')
        visit.travelers.clear()
        self.as_user(self.owner)
        self.assertEqual(self.client.delete(f'/api/visits/{visit.id}/').status_code, 204)
        self.assertFalse(Visit.objects.filter(pk=visit.pk).exists())


class AccountDeletionVisitTests(AudienceTestBase):
    def _delete_editor(self):
        from users.services.account_deletion import delete_user_account

        delete_user_account(self.editor)

    def test_visit_only_the_deleted_person_travelled_on_goes_with_them(self):
        visit = Visit.objects.create(location=self.hut, start_date='2026-06-01T00:00:00Z')
        visit.travelers.set([self.editor])
        self._delete_editor()
        self.assertFalse(Visit.objects.filter(pk=visit.pk).exists())

    def test_shared_visit_stays_with_the_others(self):
        visit = Visit.objects.create(location=self.hut, start_date='2026-06-01T00:00:00Z')
        visit.travelers.set([self.owner, self.editor])
        self._delete_editor()
        self.assertEqual([u.pk for u in Visit.objects.get(pk=visit.pk).travelers.all()], [self.owner.pk])
