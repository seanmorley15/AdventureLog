"""
Who can be named, and who is shown, is relative to the person asking: the location's owner, plus
the people they share a collection holding the location with. A trip they are not on stays hidden.
"""
from adventures.models import Collection, Location, Notification, Visit
from adventures.services import travelers
from adventures.tests.base import AudienceTestBase, make_user


def _usernames(people):
    return sorted(p['username'] for p in people)


class TravelerScopeTests(AudienceTestBase):
    """Alice (owner) has Hut in two trips: Lofoten with editor and viewer, Offsite with Carol and Dan."""

    def setUp(self):
        super().setUp()
        self.carol = make_user('carol')
        self.dan = make_user('dan')
        self.offsite = Collection.objects.create(user=self.owner, name='Offsite')
        self.offsite.shared_with.add(self.carol, self.dan)
        self.hut.collections.add(self.offsite)

    def _visit(self, who):
        visit = Visit.objects.create(location=self.hut, start_date='2026-06-01T00:00:00Z')
        visit.travelers.set(who)
        return visit

    def _candidates(self, user, query=''):
        self.as_user(user)
        response = self.client.get(f'/api/locations/{self.hut.id}/traveler-candidates/{query}')
        self.assertEqual(response.status_code, 200, response.data)
        return _usernames(response.data)

    def test_candidates_are_people_the_requester_shares_a_trip_with(self):
        self.assertEqual(self._candidates(self.editor), ['editor', 'owner', 'viewer'])
        self.assertEqual(self._candidates(self.carol), ['carol', 'dan', 'owner'])

    def test_the_location_owner_sees_every_candidate(self):
        self.assertEqual(self._candidates(self.owner), ['carol', 'dan', 'editor', 'owner', 'viewer'])

    def test_candidates_scoped_to_one_trip(self):
        self.assertEqual(
            self._candidates(self.owner, f'?collection={self.offsite.id}'), ['carol', 'dan', 'owner']
        )
        self.assertEqual(self._candidates(self.editor, f'?collection={self.trip.id}'), ['editor', 'owner', 'viewer'])
        # A trip they are not on, or one that does not hold the location, is not found.
        self.as_user(self.editor)
        url = f'/api/locations/{self.hut.id}/traveler-candidates/'
        self.assertEqual(self.client.get(f'{url}?collection={self.offsite.id}').status_code, 404)
        elsewhere = Collection.objects.create(user=self.editor, name='Mine')
        self.assertEqual(self.client.get(f'{url}?collection={elsewhere.id}').status_code, 404)
        self.assertEqual(self.client.get(f'{url}?collection=nope').status_code, 400)

    def test_service_candidates(self):
        def names(**kwargs):
            return sorted(travelers.candidates(self.hut, **kwargs).values_list('username', flat=True))

        self.assertEqual(names(requester=self.editor), ['editor', 'owner', 'viewer'])
        self.assertEqual(names(requester=self.owner), ['carol', 'dan', 'editor', 'owner', 'viewer'])
        self.assertEqual(names(requester=self.stranger), ['owner'])
        self.assertEqual(names(collection=self.offsite), ['carol', 'dan', 'owner'])

    def test_naming_someone_from_another_trip_is_refused(self):
        visit = self._visit([self.owner])
        self.as_user(self.editor)
        response = self.client.patch(
            f'/api/visits/{visit.id}/', {'traveler_uuids': [str(self.owner.uuid), str(self.carol.uuid)]},
            format='json',
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(response.data['code'], 'traveler_not_allowed')
        self.assertEqual(list(visit.travelers.all()), [self.owner])
        self.assertFalse(Notification.objects.filter(user=self.carol).exists())
        response = self.client.post(
            '/api/visits/',
            {'location': str(self.hut.id), 'start_date': '2026-06-02T00:00:00Z', 'traveler_uuids': [str(self.carol.uuid)]},
            format='json',
        )
        self.assertEqual(response.status_code, 400, response.data)

    def test_log_visit_names_only_people_on_that_trip(self):
        self.as_user(self.owner)
        url = f'/api/collections/{self.trip.id}/itinerary-items/{self.stop.id}/log-visit/'
        response = self.client.post(url, {'traveler_uuids': [str(self.carol.uuid)]}, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Visit.objects.filter(location=self.hut).exists())
        response = self.client.post(url, {'traveler_uuids': [str(self.editor.uuid)]}, format='json')
        self.assertEqual(response.status_code, 201, response.data)

    def test_travelers_from_another_trip_are_hidden(self):
        self._visit([self.owner, self.carol])
        self.as_user(self.editor)
        visit = self.client.get(f'/api/locations/{self.hut.id}/').data['visits'][0]
        self.assertEqual(_usernames(visit['travelers']), ['owner'])
        self.as_user(self.carol)
        visit = self.client.get(f'/api/locations/{self.hut.id}/').data['visits'][0]
        self.assertEqual(_usernames(visit['travelers']), ['carol', 'owner'])
        self.as_user(self.owner)
        visit = self.client.get(f'/api/locations/{self.hut.id}/').data['visits'][0]
        self.assertEqual(_usernames(visit['travelers']), ['carol', 'owner'])

    def test_a_hidden_traveler_is_kept_when_an_editor_replaces_the_list(self):
        visit = self._visit([self.owner, self.carol])
        self.as_user(self.editor)
        response = self.client.patch(
            f'/api/visits/{visit.id}/', {'traveler_uuids': [str(self.editor.uuid)]}, format='json'
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(_usernames(response.data['travelers']), ['editor'])
        self.assertEqual(sorted(visit.travelers.values_list('username', flat=True)), ['carol', 'editor'])

    def test_hidden_travelers_still_get_their_credit(self):
        self._visit([self.owner, self.carol])
        visited = Location.objects.annotate(v=travelers.visited_by(self.carol)).get(pk=self.hut.pk).v
        self.assertTrue(visited)
        self.as_user(self.carol)
        self.assertTrue(self.client.get(f'/api/locations/{self.hut.id}/').data['is_visited'])

    def test_join_is_for_people_who_reach_the_location(self):
        visit = self._visit([self.owner])
        self.as_user(self.carol)
        self.assertEqual(self.client.post(f'/api/visits/{visit.id}/join/').status_code, 200)
