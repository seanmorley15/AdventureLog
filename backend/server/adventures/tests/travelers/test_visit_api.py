from adventures.models import CollectionMember, Visit
from adventures.tests.base import AudienceTestBase


def _usernames(data):
    return sorted(t['username'] for t in data['travelers'])


class VisitTravelersApiTests(AudienceTestBase):
    def _payload(self, **extra):
        return {'location': str(self.hut.id), 'start_date': '2026-06-01T00:00:00Z', **extra}

    def _visit(self, who):
        visit = Visit.objects.create(location=self.hut, start_date='2026-06-01T00:00:00Z')
        visit.travelers.set(who)
        return visit

    def test_create_visit_defaults_to_requester(self):
        self.as_user(self.editor)
        response = self.client.post('/api/visits/', self._payload(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(_usernames(response.data), ['editor'])
        self.assertEqual([u.pk for u in Visit.objects.get(pk=response.data['id']).travelers.all()], [self.editor.pk])

    def test_editor_sets_candidates(self):
        visit = self._visit([self.owner])
        self.as_user(self.editor)
        response = self.client.patch(
            f'/api/visits/{visit.id}/',
            {'traveler_uuids': [str(self.owner.uuid), str(self.viewer.uuid)]},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(_usernames(response.data), ['owner', 'viewer'])
        self.assertNotIn('traveler_uuids', response.data)

    def test_non_candidate_rejected_400(self):
        visit = self._visit([self.owner])
        self.as_user(self.editor)
        response = self.client.patch(
            f'/api/visits/{visit.id}/', {'traveler_uuids': [str(self.stranger.uuid)]}, format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(list(visit.travelers.all()), [self.owner])
        # A rejected create leaves no visit behind.
        before = Visit.objects.count()
        response = self.client.post(
            '/api/visits/', self._payload(traveler_uuids=[str(self.stranger.uuid)]), format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Visit.objects.count(), before)

    def test_viewer_cannot_set_travelers_403(self):
        visit = self._visit([self.owner])
        self.as_user(self.viewer)
        response = self.client.patch(
            f'/api/visits/{visit.id}/', {'traveler_uuids': [str(self.viewer.uuid)]}, format='json'
        )
        self.assertEqual(response.status_code, 403)
        response = self.client.post(
            '/api/visits/', self._payload(traveler_uuids=[str(self.viewer.uuid)]), format='json'
        )
        self.assertEqual(response.status_code, 403)

    def test_viewer_join_and_leave(self):
        visit = self._visit([self.owner])
        self.as_user(self.viewer)
        response = self.client.post(f'/api/visits/{visit.id}/join/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(_usernames(response.data), ['owner', 'viewer'])
        response = self.client.post(f'/api/visits/{visit.id}/leave/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(_usernames(response.data), ['owner'])

    def test_stranger_join_404(self):
        visit = self._visit([self.owner])
        self.as_user(self.stranger)
        self.assertEqual(self.client.post(f'/api/visits/{visit.id}/join/').status_code, 404)
        self.assertEqual(self.client.post(f'/api/visits/{visit.id}/leave/').status_code, 404)
        self.as_anonymous()
        self.assertIn(self.client.post(f'/api/visits/{visit.id}/join/').status_code, (401, 403))

    def test_editor_cannot_remove_former_member(self):
        visit = self._visit([self.owner, self.editor])
        self.trip.shared_with.remove(self.editor)
        CollectionMember.objects.filter(collection=self.trip, user=self.editor).delete()
        self.as_user(self.owner)
        response = self.client.patch(
            f'/api/visits/{visit.id}/', {'traveler_uuids': [str(self.owner.uuid)]}, format='json'
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(_usernames(response.data), ['editor', 'owner'])
        # Only the former member can take themselves off.
        self.as_user(self.editor)
        response = self.client.post(f'/api/visits/{visit.id}/leave/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(list(visit.travelers.all()), [self.owner])

    def test_travelers_hidden_from_guest_link_and_public(self):
        from adventures.models import CollectionGuestLink

        visit = self._visit([self.owner])
        self.hut.is_public = True
        self.hut.save()
        link = CollectionGuestLink.objects.create(collection=self.trip, role='viewer')
        self.as_anonymous()
        public = self.client.get(f'/api/locations/{self.hut.id}/')
        self.assertEqual(public.status_code, 200)
        self.assertNotIn('travelers', public.data['visits'][0])
        guest = self.client.get(f'/api/locations/{self.hut.id}/', HTTP_X_GUEST_TOKEN=link.token)
        self.assertEqual(guest.status_code, 200)
        self.assertNotIn('travelers', guest.data['visits'][0])
        # A stranger who is signed in sees none either.
        self.as_user(self.stranger)
        self.assertNotIn('travelers', self.client.get(f'/api/locations/{self.hut.id}/').data['visits'][0])
        # A member does.
        self.as_user(self.viewer)
        self.assertEqual(_usernames(self.client.get(f'/api/locations/{self.hut.id}/').data['visits'][0]), ['owner'])
        self.assertEqual(visit.travelers.count(), 1)

    def test_candidates_endpoint_lists_owner_and_members(self):
        self.as_user(self.viewer)
        response = self.client.get(f'/api/locations/{self.hut.id}/traveler-candidates/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(sorted(u['username'] for u in response.data), ['editor', 'owner', 'viewer'])
        self.assertEqual(
            set(response.data[0]), {'uuid', 'username', 'first_name', 'last_name', 'profile_pic'}
        )
        self.as_user(self.stranger)
        self.assertEqual(self.client.get(f'/api/locations/{self.hut.id}/traveler-candidates/').status_code, 404)

    def test_last_traveler_leave_deletes_visit(self):
        visit = self._visit([self.viewer])
        self.as_user(self.viewer)
        response = self.client.post(f'/api/visits/{visit.id}/leave/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Visit.objects.filter(pk=visit.pk).exists())
