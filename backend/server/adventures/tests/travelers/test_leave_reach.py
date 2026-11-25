"""
Leaving a trip only takes the places you no longer reach: the same rule as unlinking a place.
Someone who still reaches a place through another collection keeps their visits there.
"""
from adventures.models import Collection, CollectionMember, Location, Visit
from adventures.services import travelers
from adventures.tests.base import AudienceTestBase


class LeaveKeepsPlacesStillReachedTests(AudienceTestBase):
    """Hut is in Lofoten and in a second trip, Weekend; the editor is a member of both."""

    def setUp(self):
        super().setUp()
        self.weekend = Collection.objects.create(user=self.owner, name='Weekend')
        self.weekend.shared_with.add(self.editor)
        self.hut.collections.add(self.weekend)
        self.shared = self._visit([self.owner, self.editor], '2026-06-01T00:00:00Z')
        self.alone = self._visit([self.editor], '2026-07-01T00:00:00Z')

    def _visit(self, who, start):
        visit = Visit.objects.create(location=self.hut, start_date=start)
        visit.travelers.set(who)
        return visit

    def _untouched(self):
        self.assertEqual(sorted(self.shared.travelers.values_list('username', flat=True)), ['editor', 'owner'])
        self.assertTrue(Visit.objects.filter(pk=self.alone.pk, travelers=self.editor).exists())
        self.assertFalse(Location.objects.filter(user=self.editor, name='Hut').exists())

    def test_leaving_one_trip_keeps_visits_at_a_place_another_trip_still_holds(self):
        self.as_user(self.editor)
        preview = self.client.get(f'/api/collections/{self.trip.id}/leave-preview/')
        self.assertEqual(preview.json(), {'locations': 0, 'others_uploads': 0})
        response = self.client.post(f'/api/collections/{self.trip.id}/leave/', {'keep_copies': True}, format='json')
        self.assertEqual(response.status_code, 204)
        self._untouched()
        # Leaving the second trip too now takes the place.
        preview = self.client.get(f'/api/collections/{self.weekend.id}/leave-preview/')
        self.assertEqual(preview.json()['locations'], 1)
        self.client.post(f'/api/collections/{self.weekend.id}/leave/', {'keep_copies': True}, format='json')
        self.assertEqual(Location.objects.filter(user=self.editor, name='Hut').count(), 1)
        self.assertEqual(list(self.shared.travelers.values_list('username', flat=True)), ['owner'])

    def test_owner_removal_keeps_visits_at_a_place_another_trip_still_holds(self):
        self.as_user(self.owner)
        url = f'/api/collections/{self.trip.id}/members/{self.editor.uuid}/'
        self.assertEqual(self.client.get(f'{url}removal-preview/').json(), {'locations': 0, 'others_uploads': 0})
        self.assertEqual(self.client.delete(url).status_code, 204)
        self._untouched()

    def test_a_place_in_a_collection_they_own_is_kept_too(self):
        self.weekend.shared_with.remove(self.editor)
        CollectionMember.objects.filter(collection=self.weekend, user=self.editor).delete()
        own = Collection.objects.create(user=self.editor, name='Mine')
        self.hut.collections.add(own)
        self.assertEqual(list(travelers.member_locations(self.trip, self.editor)), [])
        self.assertEqual(travelers.release_member(self.trip, self.editor, keep_copies=True), 0)
        self._untouched()

    def test_going_private_judges_all_shared_trips_at_once(self):
        self.as_user(self.editor)
        preview = self.client.get('/api/account/privacy-preview/').json()
        self.assertEqual((preview['copies'], preview['visits_deleted']), (1, 1))
        body = self.client.patch('/api/account/', {'profile_visibility': 'private'}, format='json').json()
        self.assertEqual(body['kept_copies'], 1)
        self.assertEqual(Location.objects.filter(user=self.editor, name='Hut').count(), 1)
        self.assertEqual(list(self.shared.travelers.values_list('username', flat=True)), ['owner'])
        self.assertFalse(Visit.objects.filter(pk=self.alone.pk).exists())

    def test_going_private_keeps_a_place_held_by_a_collection_they_own(self):
        own = Collection.objects.create(user=self.editor, name='Mine')
        self.hut.collections.add(own)
        self.as_user(self.editor)
        preview = self.client.get('/api/account/privacy-preview/').json()
        self.assertEqual((preview['copies'], preview['visits_deleted']), (0, 0))
        body = self.client.patch('/api/account/', {'profile_visibility': 'private'}, format='json').json()
        self.assertEqual(body['kept_copies'], 0)
        self._untouched()

    def test_preview_matches_lost_access_users(self):
        # One source of rules: what leaving takes is what lost_access_users finds with the trip ignored.
        self.assertNotIn(self.editor, travelers.lost_access_users(self.hut, ignoring=[self.trip]))
        self.assertEqual(travelers.leave_preview(self.trip, self.editor)['locations'], 0)
        self.assertIn(self.editor, travelers.lost_access_users(self.hut, ignoring=[self.trip, self.weekend]))
        self.assertEqual(travelers.leave_preview_all([self.trip, self.weekend], self.editor)['locations'], 1)
