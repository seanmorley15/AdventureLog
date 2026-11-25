from datetime import datetime, timedelta, timezone as dt_timezone

from adventures.models import Collection, Location, Visit
from adventures.services import travelers
from adventures.services.location_collections import unlink_location
from adventures.services.user_stats import UserStatsService
from adventures.tests.base import AudienceTestBase


def _past(day=1):
    return datetime(2026, 6, day, 10, 0, tzinfo=dt_timezone.utc)


class UnlinkReleasesTravelersTests(AudienceTestBase):
    """A place that leaves the last collection a traveler can reach it through is theirs to keep, as a copy."""

    def setUp(self):
        super().setUp()
        self.visit = Visit.objects.create(
            location=self.hut, start_date=_past(), end_date=_past() + timedelta(hours=20), timezone='Europe/Oslo',
        )
        self.visit.travelers.set([self.owner, self.editor])

    def _copies(self, user=None):
        return Location.objects.filter(user=user or self.editor).exclude(pk=self.hut.pk)

    def _assert_released(self):
        self.assertEqual(sorted(u.pk for u in self.visit.travelers.all()), [self.owner.pk])
        copy = self._copies().get()
        self.assertEqual(copy.name, 'Hut')
        self.assertEqual(copy.visits.count(), 1)
        self.assertEqual([u.pk for u in copy.visits.get().travelers.all()], [self.editor.pk])

    def test_delete_membership_releases_member_with_a_copy(self):
        self.as_user(self.owner)
        r = self.client.delete(f'/api/locations/{self.hut.id}/collections/{self.trip.id}/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(set(r.json()), {'linked', 'removed_placements'})
        self._assert_released()

    def test_patch_collections_releases_member_with_a_copy(self):
        self.as_user(self.owner)
        r = self.client.patch(f'/api/locations/{self.hut.id}/', {'collections': []}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self._assert_released()

    def test_traveler_in_another_collection_is_kept(self):
        other = Collection.objects.create(user=self.owner, name='Other')
        other.shared_with.add(self.editor)
        self.hut.collections.add(other)
        unlink_location(self.hut, self.trip)
        self.assertEqual(sorted(u.pk for u in self.visit.travelers.all()), sorted([self.owner.pk, self.editor.pk]))
        self.assertFalse(self._copies().exists())

    def test_owner_who_travelled_is_unaffected(self):
        unlink_location(self.hut, self.trip)
        self.assertIn(self.owner, self.visit.travelers.all())
        self.assertFalse(self._copies(self.owner).exists())

    def test_member_owned_place_stays_theirs_and_the_other_traveler_is_released(self):
        place = Location.objects.create(user=self.editor, name='Mine')
        place.collections.add(self.trip)
        visit = Visit.objects.create(location=place, start_date=_past())
        visit.travelers.set([self.editor, self.owner])
        unlink_location(place, self.trip)
        # the editor owns it and stays on it; the collection owner, now without access, gets a copy
        self.assertEqual([u.pk for u in visit.travelers.all()], [self.editor.pk])
        self.assertEqual(Location.objects.filter(user=self.owner, name='Mine').count(), 1)
        self.assertEqual(Location.objects.filter(user=self.editor, name='Mine').count(), 1)

    def test_second_run_is_a_no_op(self):
        unlink_location(self.hut, self.trip)
        unlink_location(self.hut, self.trip)
        self.assertEqual(self._copies().count(), 1)
        self.assertEqual(travelers.release_lost_access(self.hut), 0)
        self.assertEqual(self._copies().count(), 1)

    def test_stats_and_lists_after_release(self):
        self.assertEqual(UserStatsService().get_visited_locations_count(self.editor), 1)
        unlink_location(self.hut, self.trip)
        self.assertEqual(UserStatsService().get_visited_locations_count(self.editor), 1)
        self.assertFalse(Location.objects.filter(travelers.where_ive_been_q(self.editor), pk=self.hut.pk).exists())
        self.assertTrue(
            Location.objects.filter(travelers.where_ive_been_q(self.editor), pk=self._copies().get().pk).exists()
        )

    def test_deleting_the_collection_releases_members(self):
        self.as_user(self.owner)
        r = self.client.delete(f'/api/collections/{self.trip.id}/')
        self.assertEqual(r.status_code, 204, r.content)
        self.assertTrue(Location.objects.filter(pk=self.hut.pk).exists())
        self._assert_released()

    def test_deleting_the_collection_keeps_travelers_in_another_collection(self):
        other = Collection.objects.create(user=self.owner, name='Other')
        other.shared_with.add(self.editor)
        self.hut.collections.add(other)
        self.trip.delete()
        self.assertEqual(self.visit.travelers.count(), 2)
        self.assertFalse(self._copies().exists())

    def test_removing_a_member_copies_exactly_once(self):
        self.as_user(self.owner)
        r = self.client.delete(f'/api/collections/{self.trip.id}/members/{self.editor.uuid}/')
        self.assertEqual(r.status_code, 204, r.content)
        self.assertEqual(self._copies().count(), 1)
        # unlinking afterwards finds nobody left to release
        unlink_location(self.hut, self.trip)
        self.assertEqual(self._copies().count(), 1)

    def test_leave_copies_exactly_once(self):
        self.as_user(self.editor)
        r = self.client.post(f'/api/collections/{self.trip.id}/leave/', {}, format='json')
        self.assertEqual(r.status_code, 204, r.content)
        self.assertEqual(self._copies().count(), 1)
