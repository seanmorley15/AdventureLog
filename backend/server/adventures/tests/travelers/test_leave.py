from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

from adventures.models import Collection, CollectionActivity, Location, Visit
from adventures.services import travelers
from adventures.services.user_stats import UserStatsService
from adventures.tests.base import AudienceTestBase
from core.geo import make_point
from worldtravel.models import Country, Region, VisitedRegion


def _past(day=1):
    return datetime(2026, 6, day, 10, 0, tzinfo=dt_timezone.utc)


def _count(user):
    return UserStatsService().get_visited_locations_count(user)


class LeaveKeepsHistoryTests(AudienceTestBase):
    def setUp(self):
        super().setUp()
        country = Country.objects.create(name='Norway', country_code='NO', coordinates=make_point(8, 61))
        self.region = Region.objects.create(id='NO-18', name='Nordland', country=country)
        self.hut.region = self.region
        self.hut.save()
        self.visit = Visit.objects.create(
            location=self.hut, start_date=_past(), end_date=_past() + timedelta(hours=20),
            timezone='Europe/Oslo', notes='Windy night',
        )
        self.visit.travelers.set([self.owner, self.editor])
        travelers.mark_regions_for_travelers(self.hut)

    def _leave(self, user=None, **body):
        self.as_user(user or self.editor)
        return self.client.post(f'/api/collections/{self.trip.id}/leave/', body, format='json')

    def _copies(self, user=None):
        return Location.objects.filter(user=user or self.editor).exclude(pk=self.hut.pk)

    def _travelers(self, visit):
        return sorted(u.pk for u in visit.travelers.all())

    def _assert_copy_of_hut(self, visits=1):
        copies = self._copies()
        self.assertEqual(copies.count(), 1)
        copy = copies.get()
        self.assertEqual(copy.name, 'Hut')
        self.assertFalse(copy.is_public)
        self.assertEqual(list(copy.collections.all()), [])
        self.assertEqual(copy.visits.count(), visits)
        for visit in copy.visits.all():
            self.assertEqual(self._travelers(visit), [self.editor.pk])
        return copy

    # -- Leaving -----------------------------------------------------------------------

    def test_leave_with_copies(self):
        response = self._leave()
        self.assertEqual(response.status_code, 204, response.content)
        self.assertFalse(self.trip.shared_with.filter(pk=self.editor.pk).exists())

        copy = self._assert_copy_of_hut()
        visit = copy.visits.get()
        self.assertEqual(
            (visit.start_date, visit.end_date, visit.timezone, visit.notes),
            (self.visit.start_date, self.visit.end_date, 'Europe/Oslo', 'Windy night'),
        )
        self.assertEqual(copy.region_id, self.region.id)
        self.assertEqual(self._travelers(self.visit), [self.owner.pk])
        self.assertEqual(_count(self.editor), 1)
        self.assertEqual(_count(self.owner), 1)
        self.assertTrue(VisitedRegion.objects.filter(user=self.editor, region=self.region).exists())

    def test_leave_without_copies_detaches(self):
        response = self._leave(keep_copies=False)
        self.assertEqual(response.status_code, 204, response.content)
        self.assertFalse(self.trip.shared_with.filter(pk=self.editor.pk).exists())
        self.assertFalse(self._copies().exists())
        self.assertEqual(self._travelers(self.visit), [self.owner.pk])
        self.assertEqual(_count(self.editor), 0)
        # Region credit is kept per person.
        self.assertTrue(VisitedRegion.objects.filter(user=self.editor, region=self.region).exists())

    def test_leave_with_empty_body_keeps_copies(self):
        self.as_user(self.editor)
        response = self.client.post(f'/api/collections/{self.trip.id}/leave/')
        self.assertEqual(response.status_code, 204, response.content)
        self._assert_copy_of_hut()

    def test_owner_removal_always_copies(self):
        self.as_user(self.owner)
        response = self.client.delete(f'/api/collections/{self.trip.id}/members/{self.editor.uuid}/')
        self.assertEqual(response.status_code, 204, response.content)
        self.assertFalse(self.trip.shared_with.filter(pk=self.editor.pk).exists())
        self._assert_copy_of_hut()
        self.assertEqual(self._travelers(self.visit), [self.owner.pk])
        self.assertEqual(_count(self.editor), 1)
        self.assertTrue(CollectionActivity.objects.filter(
            collection=self.trip, verb=CollectionActivity.Verb.MEMBER_REMOVED,
        ).exists())

    def test_leave_dry_run_count(self):
        lake = Location.objects.create(user=self.owner, name='Lake')
        lake.collections.add(self.trip)
        Visit.objects.create(location=lake, start_date=_past(2)).travelers.set([self.editor])
        quay = Location.objects.create(user=self.owner, name='Quay')
        quay.collections.add(self.trip)
        Visit.objects.create(location=quay, start_date=_past(2)).travelers.set([self.owner])

        self.as_user(self.editor)
        response = self.client.post(f'/api/collections/{self.trip.id}/leave/?dry_run=1', {}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {'locations': 2})
        self.assertTrue(self.trip.shared_with.filter(pk=self.editor.pk).exists())
        self.assertFalse(self._copies().exists())
        self.assertEqual(self._travelers(self.visit), sorted([self.owner.pk, self.editor.pk]))
        self.assertTrue(lake.visits.filter(travelers=self.editor).exists())

    def test_own_linked_location_untouched(self):
        cabin = Location.objects.create(user=self.editor, name='Cabin')
        cabin.collections.add(self.trip)
        cabin_visit = Visit.objects.create(location=cabin, start_date=_past(2))
        cabin_visit.travelers.set([self.editor, self.owner])

        self.assertEqual(self._leave().status_code, 204)
        cabin.refresh_from_db()
        self.assertEqual(cabin.name, 'Cabin')
        self.assertTrue(cabin.collections.filter(pk=self.trip.pk).exists())
        self.assertEqual(self._travelers(cabin_visit), sorted([self.editor.pk, self.owner.pk]))
        # Only the hut was copied.
        self.assertEqual(Location.objects.filter(user=self.editor).count(), 2)
        self.assertEqual(Location.objects.filter(user=self.editor, name='Hut').count(), 1)

    def test_no_access_after_leave(self):
        self.assertEqual(self._leave().status_code, 204)
        self.as_user(self.editor)
        self.assertEqual(self.client.get(f'/api/locations/{self.hut.id}/').status_code, 404)

    def test_leaver_last_traveler_visit_is_deleted_and_copied(self):
        alone = Visit.objects.create(location=self.hut, start_date=_past(2), notes='Solo swim')
        alone.travelers.set([self.editor])

        self.assertEqual(self._leave().status_code, 204)
        self.assertFalse(Visit.objects.filter(pk=alone.pk).exists())
        self.assertEqual(self._travelers(self.visit), [self.owner.pk])
        copy = self._assert_copy_of_hut(visits=2)
        self.assertEqual(sorted(v.notes for v in copy.visits.all()), ['Solo swim', 'Windy night'])
        self.assertEqual(_count(self.editor), 1)

    def test_location_in_two_collections(self):
        other = Collection.objects.create(user=self.owner, name='Nordland highlights')
        self.hut.collections.add(other)
        earlier = Visit.objects.create(location=self.hut, start_date=_past() - timedelta(days=300))
        earlier.travelers.set([self.owner, self.editor])

        self.assertEqual(self._leave().status_code, 204)
        # Every visit of theirs at the location moves, whichever trip it was part of.
        self.assertEqual(self._travelers(self.visit), [self.owner.pk])
        self.assertEqual(self._travelers(earlier), [self.owner.pk])
        self._assert_copy_of_hut(visits=2)
        self.assertEqual(set(self.hut.collections.values_list('pk', flat=True)), {self.trip.pk, other.pk})
        self.assertEqual(_count(self.editor), 1)

    def test_failed_copy_rolls_back_the_whole_leave(self):
        lake = Location.objects.create(user=self.owner, name='Lake')
        lake.collections.add(self.trip)
        lake_visit = Visit.objects.create(location=lake, start_date=_past(2))
        lake_visit.travelers.set([self.editor])

        from adventures.services.locations import copy as copy_module
        real = copy_module.copy_location
        calls = []

        def flaky(*args, **kwargs):
            calls.append(1)
            if len(calls) > 1:
                raise RuntimeError('disk full')
            return real(*args, **kwargs)

        with patch.object(copy_module, 'copy_location', side_effect=flaky):
            with self.assertRaises(RuntimeError):
                self._leave()
        self.assertEqual(len(calls), 2)
        self.assertTrue(self.trip.shared_with.filter(pk=self.editor.pk).exists())
        self.assertFalse(self._copies().exists())
        self.assertIn(self.editor.pk, self._travelers(self.visit))
        self.assertTrue(Visit.objects.filter(pk=lake_visit.pk, travelers=self.editor).exists())

    def test_stats_unchanged_after_leaving_with_copies(self):
        lake = Location.objects.create(user=self.owner, name='Lake')
        lake.collections.add(self.trip)
        Visit.objects.create(location=lake, start_date=_past(2)).travelers.set([self.owner, self.editor])
        before = _count(self.editor)
        self.assertEqual(before, 2)
        self.assertEqual(self._leave().status_code, 204)
        self.assertEqual(_count(self.editor), before)
        self.assertEqual(_count(self.owner), 2)

    def test_owner_cannot_leave(self):
        self.assertEqual(self._leave(self.owner).status_code, 400)
        self.assertEqual(self._travelers(self.visit), sorted([self.owner.pk, self.editor.pk]))

    # -- Duplicate ---------------------------------------------------------------------

    def test_duplicate_take_my_visits(self):
        self.as_user(self.editor)
        response = self.client.post(
            f'/api/locations/{self.hut.id}/duplicate/', {'take_my_visits': True}, format='json'
        )
        self.assertEqual(response.status_code, 201, response.content)
        copy = self._assert_copy_of_hut()
        self.assertEqual(response.json()['id'], str(copy.id))
        self.assertEqual(self._travelers(self.visit), [self.owner.pk])
        # Still a member: duplicating is not leaving.
        self.assertTrue(self.trip.shared_with.filter(pk=self.editor.pk).exists())
        self.assertEqual(_count(self.editor), 1)

    def test_duplicate_without_take_my_visits_unchanged(self):
        self.as_user(self.editor)
        response = self.client.post(f'/api/locations/{self.hut.id}/duplicate/', {}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        copy = self._copies().get()
        self.assertEqual(copy.name, 'Copy of Hut')
        self.assertEqual(copy.visits.count(), 0)
        self.assertEqual(self._travelers(self.visit), sorted([self.owner.pk, self.editor.pk]))

    def test_duplicate_take_my_visits_refused_for_own_location(self):
        self.as_user(self.owner)
        response = self.client.post(
            f'/api/locations/{self.hut.id}/duplicate/', {'take_my_visits': True}, format='json'
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(Location.objects.filter(user=self.owner).count(), 1)
        self.assertEqual(self._travelers(self.visit), sorted([self.owner.pk, self.editor.pk]))
