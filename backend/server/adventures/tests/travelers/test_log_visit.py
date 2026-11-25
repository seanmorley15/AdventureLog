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

    def test_log_visit_credits_exactly_the_list(self):
        response = self._log(self.editor, [self.editor, self.owner])
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self._travelers(response), {'editor', 'owner'})

    def test_log_visit_list_without_the_actor_leaves_them_off(self):
        response = self._log(self.editor, [self.owner])
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self._travelers(response), {'owner'})

    def test_log_visit_empty_list_is_400(self):
        response = self._log(self.editor, [])
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('at least one traveler', str(response.data))
        self.assertFalse(Visit.objects.filter(location=self.hut).exists())

    def test_log_visit_omitted_list_credits_only_the_actor(self):
        response = self._log(self.editor)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self._travelers(response), {'editor'})

    def test_log_visit_non_collaborator_400(self):
        response = self._log(self.editor, [self.stranger])
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Visit.objects.filter(location=self.hut).exists())

    def test_logged_stop_with_a_list_without_the_actor(self):
        self._log(self.owner)
        second = self._log(self.editor, [self.viewer])
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(self._travelers(second), {'owner', 'viewer'})

    def test_logged_stop_adds_clicker(self):
        first = self._log(self.owner)
        self.assertEqual(first.status_code, 201)
        second = self._log(self.editor)
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(second.data['visit']['id'], first.data['visit']['id'])
        self.assertEqual(self._travelers(second), {'owner', 'editor'})
        self.assertEqual(Visit.objects.filter(location=self.hut).count(), 1)

    def test_log_visit_with_an_empty_list_is_traveler_required(self):
        self.as_user(self.editor)
        response = self.client.post(self._url(), {'traveler_uuids': []}, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(response.data['code'], 'traveler_required')

    def test_log_day_with_a_list_excluding_the_actor(self):
        self.as_user(self.editor)
        day = get_day_by_index(self.trip, 1)
        url = f'/api/collections/{self.trip.id}/days/{day.id}/log-visit/'
        empty = self.client.post(url, {'traveler_uuids': []}, format='json')
        self.assertEqual(empty.status_code, 400, empty.data)
        self.assertEqual(empty.data['code'], 'traveler_required')
        response = self.client.post(url, {'traveler_uuids': [str(self.owner.uuid)]}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        visit = Visit.objects.get(pk=response.data['visits'][0]['id'])
        self.assertEqual(set(visit.travelers.values_list('username', flat=True)), {'owner'})

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
                {'viewer'},
            )

    def test_log_visit_dedupes_travelers(self):
        response = self._log(self.editor, [self.editor, self.owner, self.owner])
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self._travelers(response), {'editor', 'owner'})


class GuestEditorLogVisitTests(AudienceTestBase):
    def setUp(self):
        super().setUp()
        from adventures.models import CollectionGuestLink

        self.link = CollectionGuestLink.objects.create(collection=self.trip, role='editor')
        self.as_anonymous()

    def _post(self, url):
        return self.client.post(url, {}, format='json', HTTP_X_GUEST_TOKEN=self.link.token)

    def test_guest_editor_logs_a_stop_for_the_owner(self):
        response = self._post(f'/api/collections/{self.trip.id}/itinerary-items/{self.stop.id}/log-visit/')
        self.assertEqual(response.status_code, 201, response.data)
        visit = Visit.objects.get(pk=response.data['visit']['id'])
        self.assertEqual(list(visit.travelers.values_list('username', flat=True)), ['owner'])

    def test_guest_editor_logs_an_already_logged_stop(self):
        first = self._post(f'/api/collections/{self.trip.id}/itinerary-items/{self.stop.id}/log-visit/')
        self.assertEqual(first.status_code, 201, first.data)
        second = self._post(f'/api/collections/{self.trip.id}/itinerary-items/{self.stop.id}/log-visit/')
        self.assertEqual(second.status_code, 200, second.data)
        visit = Visit.objects.get(pk=second.data['visit']['id'])
        self.assertEqual(list(visit.travelers.values_list('username', flat=True)), ['owner'])

    def test_log_day_with_an_anonymous_actor_credits_the_owner(self):
        # The day endpoint itself needs an account, but the service takes whatever actor it is given.
        from django.contrib.auth.models import AnonymousUser

        from adventures.services.day_plan import log_day

        day = get_day_by_index(self.trip, 1)
        logged = log_day(self.trip, day, None, None, AnonymousUser())
        self.assertEqual(len(logged), 1)
        visit = Visit.objects.get(location=self.hut)
        self.assertEqual(list(visit.travelers.values_list('username', flat=True)), ['owner'])
