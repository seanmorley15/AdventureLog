"""Dry runs that say who would get a copy, and what would go, before a place or a collection goes."""
import shutil
import tempfile
from datetime import datetime, timezone as dt_timezone

from django.core.files.base import ContentFile
from django.test import override_settings

from adventures.models import Collection, ContentImage, Location, Visit
from adventures.tests.base import AudienceTestBase
from adventures.tests.factories import PNG


def _past(day=1):
    return datetime(2026, 6, day, 10, 0, tzinfo=dt_timezone.utc)


class PreviewBase(AudienceTestBase):
    def setUp(self):
        super().setUp()
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root)
        override.enable()
        self.addCleanup(override.disable)
        self.visit = Visit.objects.create(location=self.hut, start_date=_past())
        self.visit.travelers.set([self.owner, self.editor])

    def _alone_with_a_photo_from_the_owner(self):
        alone = Visit.objects.create(location=self.hut, start_date=_past(2))
        alone.travelers.set([self.editor])
        ContentImage.objects.create(user=self.owner, image=ContentFile(PNG, name='x.png'), content_object=alone)
        return alone

    def _state(self):
        return (
            Location.objects.count(), Visit.objects.count(), ContentImage.objects.count(),
            sorted(t.pk for v in Visit.objects.all() for t in v.travelers.all()),
            self.hut.collections.count(), Collection.objects.count(),
        )


class UnlinkPreviewTests(PreviewBase):
    def _preview(self, user=None, location=None, collection=None):
        self.as_user(user or self.owner)
        location = location or self.hut
        return self.client.delete(f'/api/locations/{location.id}/collections/{(collection or self.trip).id}/?dry_run=1')

    def test_lists_who_would_get_a_copy_and_changes_nothing(self):
        before = self._state()
        response = self._preview()
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual([p['username'] for p in body['people_released']], ['editor'])
        self.assertEqual(set(body['people_released'][0]), {'uuid', 'username', 'first_name', 'last_name', 'profile_pic'})
        self.assertEqual(
            {k: v for k, v in body.items() if k != 'people_released'},
            {'includes_you': False, 'visits_deleted': 0, 'others_uploads': 0, 'removed_placements': 1},
        )
        self.assertEqual(self._state(), before)

    def test_counts_visits_that_would_go_and_uploads_of_others_on_them(self):
        self._alone_with_a_photo_from_the_owner()
        body = self._preview().json()
        self.assertEqual((body['visits_deleted'], body['others_uploads']), (1, 1))

    def test_a_traveler_who_reaches_the_place_another_way_is_not_listed(self):
        other = Collection.objects.create(user=self.owner, name='Other')
        other.shared_with.add(self.editor)
        self.hut.collections.add(other)
        body = self._preview().json()
        self.assertEqual((body['people_released'], body['visits_deleted']), ([], 0))

    def test_the_collection_owner_who_travelled_to_a_members_place_is_released_and_told_so(self):
        place = Location.objects.create(user=self.editor, name='Mine')
        place.collections.add(self.trip)
        Visit.objects.create(location=place, start_date=_past()).travelers.set([self.editor, self.owner])
        body = self._preview(location=place).json()
        self.assertEqual([p['username'] for p in body['people_released']], ['owner'])
        self.assertTrue(body['includes_you'])

    def test_the_place_owner_unlinking_from_someone_elses_trip_gets_a_preview(self):
        place = Location.objects.create(user=self.editor, name='Mine')
        place.collections.add(self.trip)
        Visit.objects.create(location=place, start_date=_past()).travelers.set([self.editor, self.owner])
        self.assertEqual(self._preview(user=self.editor, location=place).status_code, 200)

    def test_someone_who_may_not_unlink_gets_403(self):
        self.assertEqual(self._preview(user=self.editor).status_code, 403)
        self.assertEqual(self._preview(user=self.viewer).status_code, 403)

    def test_the_real_delete_keeps_its_shape(self):
        self.as_user(self.owner)
        response = self.client.delete(f'/api/locations/{self.hut.id}/collections/{self.trip.id}/')
        self.assertEqual(set(response.json()), {'linked', 'removed_placements'})


class CollectionDeletePreviewTests(PreviewBase):
    def _preview(self, user=None):
        self.as_user(user or self.owner)
        return self.client.delete(f'/api/collections/{self.trip.id}/?dry_run=1')

    def test_aggregates_over_its_places_and_changes_nothing(self):
        lake = Location.objects.create(user=self.owner, name='Lake')
        lake.collections.add(self.trip)
        Visit.objects.create(location=lake, start_date=_past()).travelers.set([self.owner, self.editor, self.viewer])
        self._alone_with_a_photo_from_the_owner()
        before = self._state()
        response = self._preview()
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(sorted(p['username'] for p in body['people_released']), ['editor', 'viewer'])
        self.assertEqual((body['places'], body['visits_deleted'], body['others_uploads']), (2, 1, 1))
        self.assertEqual(self._state(), before)
        self.assertTrue(Collection.objects.filter(pk=self.trip.pk).exists())

    def test_a_place_in_another_collection_of_theirs_releases_nobody(self):
        other = Collection.objects.create(user=self.owner, name='Other')
        other.shared_with.add(self.editor)
        self.hut.collections.add(other)
        body = self._preview().json()
        self.assertEqual((body['people_released'], body['places']), ([], 0))

    def test_only_the_owner_may_ask(self):
        self.assertIn(self._preview(user=self.editor).status_code, (403, 404))
        self.assertTrue(Collection.objects.filter(pk=self.trip.pk).exists())

    def test_the_real_delete_still_deletes(self):
        self.as_user(self.owner)
        self.assertEqual(self.client.delete(f'/api/collections/{self.trip.id}/').status_code, 204)
        self.assertFalse(Collection.objects.filter(pk=self.trip.pk).exists())


class AccountPreviewTests(PreviewBase):
    def test_deletion_preview_says_what_goes_and_who_gets_copies(self):
        # The owner's own place, travelled on by the editor; a shared trip the owner is a member of.
        theirs = Collection.objects.create(user=self.stranger, name='Theirs')
        theirs.shared_with.add(self.owner)
        spot = Location.objects.create(user=self.stranger, name='Spot')
        spot.collections.add(theirs)
        Visit.objects.create(location=spot, start_date=_past()).travelers.set([self.owner])
        Visit.objects.create(location=spot, start_date=_past(2)).travelers.set([self.owner, self.stranger])
        before = self._state()

        self.as_user(self.owner)
        response = self.client.get('/api/account/deletion-preview/')
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual([p['username'] for p in body['people_released']], ['editor'])
        self.assertEqual(
            {k: v for k, v in body.items() if k != 'people_released'},
            {
                'locations': 1, 'collections': 1, 'shared_collections_left': 1, 'places_copied': 1,
                'visits_detached': 1, 'visits_deleted': 1, 'others_uploads': 0,
            },
        )
        self.assertEqual(self._state(), before)

    def test_needs_a_session(self):
        self.as_anonymous()
        self.assertIn(self.client.get('/api/account/deletion-preview/').status_code, (401, 403))

    def test_privacy_preview_counts_trips_left_and_copies_kept(self):
        self.as_user(self.editor)
        before = self._state()
        body = self.client.get('/api/account/privacy-preview/').json()
        self.assertEqual(
            body,
            {'left_shared_collections': 1, 'revoked_collection_invites': 0, 'copies': 1,
             'visits_deleted': 0, 'others_uploads': 0},
        )
        self.assertEqual(self._state(), before)

    def test_going_private_reports_the_copies_it_made(self):
        self.editor.profile_visibility = 'public'
        self.editor.save()
        self.as_user(self.editor)
        response = self.client.patch('/api/account/', {'profile_visibility': 'private'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual((body['left_shared_collections'], body['kept_copies']), (1, 1))
