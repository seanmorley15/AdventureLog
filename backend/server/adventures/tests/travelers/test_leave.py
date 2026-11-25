import shutil
import tempfile
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.test import override_settings

from adventures.models import Activity, Collection, CollectionActivity, ContentAttachment, ContentImage, Location, Visit
from adventures.services import travelers
from adventures.services.user_stats import UserStatsService
from adventures.tests.base import AudienceTestBase
from adventures.tests.factories import GPX, PNG
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

    def test_leave_preview_count(self):
        lake = Location.objects.create(user=self.owner, name='Lake')
        lake.collections.add(self.trip)
        Visit.objects.create(location=lake, start_date=_past(2)).travelers.set([self.editor])
        quay = Location.objects.create(user=self.owner, name='Quay')
        quay.collections.add(self.trip)
        Visit.objects.create(location=quay, start_date=_past(2)).travelers.set([self.owner])

        self.as_user(self.editor)
        response = self.client.get(f'/api/collections/{self.trip.id}/leave-preview/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {'locations': 2, 'others_uploads': 0})
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


class LeaveCopiesUploadsTests(AudienceTestBase):
    """What the leaver added to their visits comes with their copy; nobody else's does."""

    def setUp(self):
        super().setUp()
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root)
        override.enable()
        self.addCleanup(override.disable)

    def _visit(self, who, day=1):
        visit = Visit.objects.create(location=self.hut, start_date=_past(day))
        visit.travelers.set(who)
        return visit

    def _photo(self, user, target, name='photo.png'):
        return ContentImage.objects.create(user=user, image=ContentFile(PNG, name=name), content_object=target)

    def _attachment(self, user, target, name='permit'):
        return ContentAttachment.objects.create(
            user=user, file=ContentFile(b'permit 42', name=f'{name}.txt'), name=name, content_object=target
        )

    def _activity(self, user, visit, name='Ridge hike'):
        return Activity.objects.create(
            user=user, visit=visit, name=name, sport_type='Hike', distance=5400.0,
            gpx_file=ContentFile(GPX, name='ridge.gpx'),
        )

    def _leave(self, **body):
        self.as_user(self.editor)
        response = self.client.post(f'/api/collections/{self.trip.id}/leave/', body, format='json')
        self.assertEqual(response.status_code, 204, response.content)

    def _copy_visit(self):
        copy = Location.objects.get(user=self.editor, name='Hut')
        return copy.visits.get()

    @staticmethod
    def _read(field):
        field.open('rb')
        try:
            return field.read()
        finally:
            field.close()

    def test_sole_traveler_uploads_are_copied_and_original_deleted(self):
        alone = self._visit([self.editor])
        photo = self._photo(self.editor, alone)
        attachment = self._attachment(self.editor, alone)
        activity = self._activity(self.editor, alone)
        self._photo(self.editor, activity, name='summit.png')
        owners_run = self._activity(self.owner, alone, name="Owner's run")
        originals = {'photo': photo.image.name, 'attachment': attachment.file.name, 'gpx': activity.gpx_file.name}
        photo_bytes = self._read(photo.image)

        self._leave()
        self.assertFalse(Visit.objects.filter(pk=alone.pk).exists())
        # Intended: a visit nobody travelled on any more goes, with what others added to it
        # (the dry run counts those as ``others_uploads`` so the dialog can warn).
        self.assertFalse(Activity.objects.filter(pk=owners_run.pk).exists())
        visit = self._copy_visit()

        [new_photo] = visit.images.all()
        self.assertEqual(new_photo.user, self.editor)
        # The copy shares the stored file: the original's delete leaves it for the copy.
        self.assertEqual(new_photo.image.name, originals['photo'])
        self.assertEqual(self._read(new_photo.image), photo_bytes)

        [new_attachment] = visit.attachments.all()
        self.assertEqual((new_attachment.user, new_attachment.name), (self.editor, 'permit'))
        self.assertEqual(new_attachment.file.name, originals['attachment'])
        self.assertEqual(self._read(new_attachment.file), b'permit 42')

        [new_activity] = visit.activities.all()
        self.assertEqual(
            (new_activity.user, new_activity.name, new_activity.sport_type, new_activity.distance),
            (self.editor, 'Ridge hike', 'Hike', 5400.0),
        )
        self.assertEqual((new_activity.day_id, new_activity.collection_id, new_activity.trail_id), (None, None, None))
        self.assertIsNone(new_activity.promoted_activity_id)
        self.assertEqual(new_activity.gpx_file.name, originals['gpx'])
        self.assertEqual(self._read(new_activity.gpx_file), GPX)
        self.assertEqual([p.user for p in new_activity.images.all()], [self.editor])

    def test_shared_visit_copies_only_the_leavers_uploads(self):
        shared = self._visit([self.owner, self.editor])
        mine = self._photo(self.editor, shared, name='mine.png')
        theirs = self._photo(self.owner, shared, name='theirs.png')
        my_note = self._attachment(self.editor, shared, name='mine')
        their_note = self._attachment(self.owner, shared, name='theirs')
        my_run = self._activity(self.editor, shared, name='My run')
        their_run = self._activity(self.owner, shared, name='Their run')

        self._leave()
        visit = self._copy_visit()
        self.assertEqual([p.user for p in visit.images.all()], [self.editor])
        self.assertEqual([a.name for a in visit.attachments.all()], ['mine'])
        self.assertEqual([a.name for a in visit.activities.all()], ['My run'])

        # The original visit keeps everything, the leaver's uploads included.
        self.assertEqual({p.pk for p in shared.images.all()}, {mine.pk, theirs.pk})
        self.assertEqual({a.pk for a in shared.attachments.all()}, {my_note.pk, their_note.pk})
        self.assertEqual({a.pk for a in shared.activities.all()}, {my_run.pk, their_run.pk})
        my_run.refresh_from_db()
        self.assertEqual((my_run.visit_id, self._read(my_run.gpx_file)), (shared.pk, GPX))

    def test_leaving_without_copies_copies_nothing(self):
        shared = self._visit([self.owner, self.editor])
        self._photo(self.editor, shared)
        self._attachment(self.editor, shared)
        self._activity(self.editor, shared)
        before = (ContentImage.objects.count(), ContentAttachment.objects.count(), Activity.objects.count())

        self._leave(keep_copies=False)
        self.assertFalse(Location.objects.filter(user=self.editor).exists())
        self.assertEqual(
            (ContentImage.objects.count(), ContentAttachment.objects.count(), Activity.objects.count()), before
        )

    def test_duplicate_take_my_visits_copies_uploads(self):
        shared = self._visit([self.owner, self.editor])
        self._photo(self.editor, shared, name='mine.png')
        self._photo(self.owner, shared, name='theirs.png')
        self._activity(self.editor, shared, name='My run')

        self.as_user(self.editor)
        response = self.client.post(
            f'/api/locations/{self.hut.id}/duplicate/', {'take_my_visits': True}, format='json'
        )
        self.assertEqual(response.status_code, 201, response.content)
        visit = self._copy_visit()
        self.assertEqual([p.user for p in visit.images.all()], [self.editor])
        self.assertEqual([a.name for a in visit.activities.all()], ['My run'])
        self.assertEqual(shared.images.count(), 2)

    # -- Files missing from storage --------------------------------------------------------

    def test_owner_removal_carries_a_missing_attachment_file_over(self):
        alone = self._visit([self.editor])
        attachment = self._attachment(self.editor, alone)
        attachment.file.storage.delete(attachment.file.name)

        self.as_user(self.owner)
        response = self.client.delete(f'/api/collections/{self.trip.id}/members/{self.editor.uuid}/')
        self.assertEqual(response.status_code, 204, response.content)
        self.assertFalse(self.trip.shared_with.filter(pk=self.editor.pk).exists())
        visit = self._copy_visit()
        # Nothing is read: the copy points at the same missing file, as the original did.
        self.assertEqual(list(visit.attachments.values_list('file', flat=True)), [attachment.file.name])

    def test_leave_carries_missing_photos_and_tracks_over(self):
        hut_photo = self._photo(self.owner, self.hut, name='hut.png')
        alone = self._visit([self.editor])
        visit_photo = self._photo(self.editor, alone)
        run = self._activity(self.editor, alone)
        kept = self._attachment(self.editor, alone)
        missing = {field.name for field in (hut_photo.image, visit_photo.image, run.gpx_file)}
        for field in (hut_photo.image, visit_photo.image, run.gpx_file):
            field.storage.delete(field.name)

        self._leave()
        # Nothing is read or checked: each copy points at the same (missing) file as the original.
        copy = Location.objects.get(user=self.editor, name='Hut')
        visit = copy.visits.get()
        [new_run] = visit.activities.all()
        self.assertEqual((new_run.name, new_run.distance), ('Ridge hike', 5400.0))
        self.assertEqual(
            {copy.images.get().image.name, visit.images.get().image.name, new_run.gpx_file.name}, missing
        )
        self.assertEqual([a.name for a in visit.attachments.all()], [kept.name])

    # -- Previews ----------------------------------------------------------------------

    def _rows(self):
        return (
            ContentImage.objects.count(), ContentAttachment.objects.count(), Activity.objects.count(),
            Visit.objects.count(), Location.objects.count(), self.trip.shared_with.count(),
        )

    def test_preview_counts_others_uploads_on_visits_that_would_go(self):
        alone = self._visit([self.editor])
        self._photo(self.editor, alone, name='mine.png')
        self._photo(self.owner, alone, name='theirs.png')
        self._attachment(self.viewer, alone, name='viewers')
        self._activity(self.owner, alone, name="Owner's run")
        my_run = self._activity(self.editor, alone, name='My run')
        self._photo(self.owner, my_run, name='cheer.png')
        # A visit the owner was also on survives, so nothing on it counts.
        shared = self._visit([self.owner, self.editor], day=2)
        self._photo(self.owner, shared, name='shared.png')
        before = self._rows()

        self.as_user(self.editor)
        response = self.client.get(f'/api/collections/{self.trip.id}/leave-preview/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {'locations': 1, 'others_uploads': 4})
        self.assertEqual(self._rows(), before)

    def test_preview_with_only_own_uploads(self):
        alone = self._visit([self.editor])
        self._photo(self.editor, alone)
        self._activity(self.editor, alone)

        self.as_user(self.editor)
        response = self.client.get(f'/api/collections/{self.trip.id}/leave-preview/')
        self.assertEqual(response.json(), {'locations': 1, 'others_uploads': 0})

    def test_member_removal_preview(self):
        alone = self._visit([self.editor])
        self._photo(self.owner, alone)
        before = self._rows()

        self.as_user(self.owner)
        response = self.client.get(f'/api/collections/{self.trip.id}/members/{self.editor.uuid}/removal-preview/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {'locations': 1, 'others_uploads': 1})
        self.assertEqual(self._rows(), before)
        self.assertTrue(self.trip.shared_with.filter(pk=self.editor.pk).exists())


class PrivateProfileLeavesTripsTests(AudienceTestBase):
    def test_going_private_keeps_copies_and_leaves_the_visits(self):
        visit = Visit.objects.create(location=self.hut, start_date='2026-06-01T00:00:00Z')
        visit.travelers.set([self.owner, self.editor])
        self.as_user(self.editor)
        response = self.client.patch('/api/account/', {'profile_visibility': 'private'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(self.trip.shared_with.filter(pk=self.editor.pk).exists())
        self.assertEqual([u.pk for u in visit.travelers.all()], [self.owner.pk])
        copy = Location.objects.get(user=self.editor, name='Hut')
        self.assertEqual([u.pk for u in copy.visits.get().travelers.all()], [self.editor.pk])
