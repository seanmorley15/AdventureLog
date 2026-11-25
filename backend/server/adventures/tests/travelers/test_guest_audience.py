"""Guest links never learn who travelled, and a guest who logs a visit is named by their link."""
from adventures.models import CollectionActivity, CollectionGuestLink, Notification, Visit
from adventures.tests.base import AudienceTestBase


class GuestAudienceTests(AudienceTestBase):
    def setUp(self):
        super().setUp()
        self.link = CollectionGuestLink.objects.create(collection=self.trip, role='editor', label='Grandma')

    def test_travelers_added_activity_holds_counts_not_names(self):
        visit = Visit.objects.create(location=self.hut, start_date='2026-06-01T00:00:00Z')
        visit.travelers.set([self.owner])
        self.stop.logged_visit = visit
        self.stop.save()
        self.as_user(self.owner)
        response = self.client.post(
            f'/api/collections/{self.trip.id}/add-travelers/',
            {'user_uuids': [str(self.editor.uuid), str(self.viewer.uuid)]}, format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        event = CollectionActivity.objects.get(verb=CollectionActivity.Verb.TRAVELERS_ADDED)
        self.assertEqual(event.data, {'people': 2, 'visits': 1, 'locations': 1})
        # What an editor guest link reads.
        self.as_anonymous()
        feed = self.client.get(f'/api/collections/{self.trip.id}/activity/', HTTP_X_GUEST_TOKEN=self.link.token)
        self.assertEqual(feed.status_code, 200, feed.content)
        self.assertNotIn('editor', str(feed.content))
        self.assertNotIn('viewer', str(feed.content))

    def test_guest_logging_a_visit_is_named_by_its_link(self):
        self.as_anonymous()
        response = self.client.post(
            f'/api/collections/{self.trip.id}/itinerary-items/{self.stop.id}/log-visit/',
            {'traveler_uuids': [str(self.editor.uuid)]}, format='json', HTTP_X_GUEST_TOKEN=self.link.token,
        )
        self.assertEqual(response.status_code, 201, response.data)
        visit = Visit.objects.get(pk=response.data['visit']['id'])
        self.assertEqual(list(visit.travelers.values_list('username', flat=True)), ['editor'])
        note = Notification.objects.get(user=self.editor)
        self.assertEqual((note.actor_user, note.actor_name), (None, 'Grandma'))

    def test_guest_logging_an_already_logged_stop_is_named_by_its_link(self):
        visit = Visit.objects.create(location=self.hut, start_date='2026-06-01T00:00:00Z')
        visit.travelers.set([self.owner])
        self.stop.logged_visit = visit
        self.stop.save()
        self.as_anonymous()
        response = self.client.post(
            f'/api/collections/{self.trip.id}/itinerary-items/{self.stop.id}/log-visit/',
            {'traveler_uuids': [str(self.viewer.uuid)]}, format='json', HTTP_X_GUEST_TOKEN=self.link.token,
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Notification.objects.get(user=self.viewer).actor_name, 'Grandma')
        self.assertEqual(sorted(visit.travelers.values_list('username', flat=True)), ['owner', 'viewer'])

    def test_legacy_rows_with_usernames_are_read_without_them(self):
        CollectionActivity.objects.create(
            collection=self.trip, verb=CollectionActivity.Verb.TRAVELERS_ADDED, actor_user=self.owner,
            actor_name='owner', data={'usernames': ['editor', 'viewer'], 'visits': 2, 'locations': 1},
        )
        self.as_anonymous()
        feed = self.client.get(f'/api/collections/{self.trip.id}/activity/', HTTP_X_GUEST_TOKEN=self.link.token)
        self.assertEqual(feed.status_code, 200, feed.content)
        event = next(e for e in feed.json() if e['verb'] == 'travelers_added')
        self.assertEqual(event['data'], {'visits': 2, 'locations': 1, 'people': 2})
