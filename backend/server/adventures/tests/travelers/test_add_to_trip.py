from datetime import datetime, timezone as tz

from adventures.models import CollectionActivity, CollectionItineraryItem, Location, Visit
from adventures.tests.base import AudienceTestBase


def at(y, m, d, hour=12):
    return datetime(y, m, d, hour, tzinfo=tz.utc)


class AddToTripTests(AudienceTestBase):
    def _url(self, dry_run=False):
        return f'/api/collections/{self.trip.id}/add-travelers/' + ('?dry_run=1' if dry_run else '')

    def _post(self, user, who, dry_run=False):
        self.as_user(user)
        return self.client.post(self._url(dry_run), {'user_uuids': [str(u.uuid) for u in who]}, format='json')

    def _travelers(self, visit):
        return set(visit.travelers.values_list('username', flat=True))

    def _visit(self, location, when, who):
        visit = Visit.objects.create(location=location, start_date=when)
        visit.travelers.set(who)
        return visit

    def test_add_travelers_dated_trip(self):
        june = self._visit(self.hut, at(2026, 6, 2), [self.owner])
        old = self._visit(self.hut, at(2025, 1, 1), [self.owner])
        response = self._post(self.owner, [self.editor])
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.json(), {'visits': 1, 'locations': 1})
        self.assertEqual(self._travelers(june), {'owner', 'editor'})
        self.assertEqual(self._travelers(old), {'owner'})
        self.assertTrue(CollectionActivity.objects.filter(
            collection=self.trip, verb=CollectionActivity.Verb.TRAVELERS_ADDED).exists())

    def test_dated_trip_includes_whole_last_day(self):
        late = self._visit(self.hut, at(2026, 6, 3, 23), [self.owner])
        after = self._visit(self.hut, at(2026, 6, 4, 1), [self.owner])
        self.assertEqual(self._post(self.editor, [self.editor]).json(), {'visits': 1, 'locations': 1})
        self.assertIn('editor', self._travelers(late))
        self.assertNotIn('editor', self._travelers(after))

    def test_visit_that_already_has_them_is_not_counted(self):
        self._visit(self.hut, at(2026, 6, 2), [self.owner, self.editor])
        self.assertEqual(self._post(self.owner, [self.editor]).json(), {'visits': 0, 'locations': 0})

    def test_add_travelers_undated_trip_only_logged_visits(self):
        self.trip.start_date = None
        self.trip.end_date = None
        self.trip.save()
        logged = self._visit(self.hut, at(2026, 6, 2), [self.owner])
        unlogged = self._visit(self.hut, at(2026, 6, 2), [self.owner])
        CollectionItineraryItem.objects.filter(pk=self.stop.pk).update(logged_visit=logged)
        response = self._post(self.owner, [self.editor])
        self.assertEqual(response.json(), {'visits': 1, 'locations': 1})
        self.assertEqual(self._travelers(logged), {'owner', 'editor'})
        self.assertEqual(self._travelers(unlogged), {'owner'})

    def test_dry_run_changes_nothing(self):
        visit = self._visit(self.hut, at(2026, 6, 2), [self.owner])
        response = self._post(self.owner, [self.editor], dry_run=True)
        self.assertEqual(response.json(), {'visits': 1, 'locations': 1})
        self.assertEqual(self._travelers(visit), {'owner'})
        self.assertFalse(CollectionActivity.objects.filter(verb=CollectionActivity.Verb.TRAVELERS_ADDED).exists())

    def test_viewer_forbidden(self):
        self.assertEqual(self._post(self.viewer, [self.viewer]).status_code, 403)

    def test_non_member_forbidden_or_hidden(self):
        self.assertEqual(self._post(self.stranger, [self.stranger]).status_code, 404)

    def test_non_member_uuid_400(self):
        visit = self._visit(self.hut, at(2026, 6, 2), [self.owner])
        response = self._post(self.owner, [self.editor, self.stranger])
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(self._travelers(visit), {'owner'})

    def test_duplicate_uuids_are_fine(self):
        self._visit(self.hut, at(2026, 6, 2), [self.owner])
        self.as_user(self.owner)
        uuid = str(self.editor.uuid)
        response = self.client.post(self._url(), {'user_uuids': [uuid, uuid]}, format='json')
        self.assertEqual(response.json(), {'visits': 1, 'locations': 1})

    def test_counts_distinct_locations(self):
        other = Location.objects.create(user=self.owner, name='Pier', is_public=False)
        other.collections.add(self.trip)
        self._visit(self.hut, at(2026, 6, 1), [self.owner])
        self._visit(self.hut, at(2026, 6, 2), [self.owner])
        self._visit(other, at(2026, 6, 2), [self.owner])
        self.assertEqual(self._post(self.owner, [self.editor]).json(), {'visits': 3, 'locations': 2})


class AddTravelersBadIdTests(AudienceTestBase):
    def test_malformed_collection_id_is_404(self):
        self.as_user(self.owner)
        for path in ('add-travelers/', 'leave/', 'leave/?dry_run=1'):
            response = self.client.post(f'/api/collections/not-a-uuid/{path}', {}, format='json')
            self.assertEqual(response.status_code, 404, (path, response.content))
