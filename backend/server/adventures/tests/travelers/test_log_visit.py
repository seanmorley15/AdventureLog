from django.contrib.contenttypes.models import ContentType

from adventures.models import Location, Visit
from adventures.services.day_plan import get_day_by_index, place_object
from adventures.tests.base import AudienceTestBase


class LogVisitTravelersTests(AudienceTestBase):
    def _url(self, stop=None):
        return f'/api/collections/{self.trip.id}/itinerary-items/{(stop or self.stop).id}/log-visit/'

    def _log(self, user, ids=None, stop=None):
        self.as_user(user)
        body = {} if ids is None else {'traveler_uuids': [str(u.uuid) for u in ids]}
        return self.client.post(self._url(stop), body, format='json')

    def _travelers(self, response):
        return set(Visit.objects.get(pk=response.data['visit']['id']).travelers.values_list('username', flat=True))

    def test_log_visit_credits_clicker_and_ticked(self):
        response = self._log(self.editor, [self.owner])
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self._travelers(response), {'editor', 'owner'})

    def test_log_visit_alone_credits_only_clicker(self):
        response = self._log(self.editor)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self._travelers(response), {'editor'})

    def test_log_visit_non_collaborator_400(self):
        response = self._log(self.editor, [self.stranger])
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Visit.objects.filter(location=self.hut).exists())

    def test_logged_stop_adds_clicker(self):
        first = self._log(self.owner)
        self.assertEqual(first.status_code, 201)
        second = self._log(self.editor)
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(second.data['visit']['id'], first.data['visit']['id'])
        self.assertEqual(self._travelers(second), {'owner', 'editor'})
        self.assertEqual(Visit.objects.filter(location=self.hut).count(), 1)

    def test_existing_visit_on_same_dates_gains_clicker(self):
        visit = Visit.objects.create(location=self.hut, start_date='2026-06-01T00:00:00Z', end_date='2026-06-01T23:59:59Z')
        visit.travelers.set([self.owner])
        response = self._log(self.editor)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['visit']['id'], str(visit.id))
        self.assertEqual(set(visit.travelers.values_list('username', flat=True)), {'owner', 'editor'})

    def test_log_day_applies_travelers_to_each_stop(self):
        other = Location.objects.create(user=self.owner, name='Pier', is_public=False)
        other.collections.add(self.trip)
        place_object(
            self.trip, ContentType.objects.get_for_model(Location), other.id, day=get_day_by_index(self.trip, 1)
        )
        self.as_user(self.editor)
        day = get_day_by_index(self.trip, 1)
        response = self.client.post(
            f'/api/collections/{self.trip.id}/days/{day.id}/log-visit/',
            {'traveler_uuids': [str(self.viewer.uuid)]}, format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data['visits']), 2)
        for visit in response.data['visits']:
            self.assertEqual(
                set(Visit.objects.get(pk=visit['id']).travelers.values_list('username', flat=True)),
                {'editor', 'viewer'},
            )

    def test_log_visit_dedupes_travelers(self):
        response = self._log(self.editor, [self.editor, self.owner, self.owner])
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self._travelers(response), {'editor', 'owner'})
