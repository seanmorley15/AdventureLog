"""Duplicating a collection: what is copied, what is shared with the original, and what is left behind."""

import shutil
import tempfile

from django.test import override_settings
from rest_framework.test import APITestCase

from adventures.models import (
    Checklist, Collection, CollectionComment, CollectionInvite, CollectionItineraryDay,
    CollectionItineraryItem, ContentAttachment, ContentImage, Location, Lodging, Note, Transportation,
)
from adventures.tests.factories import build_rich_account
from users.models import CustomUser


class DuplicateCollectionTests(APITestCase):
    def setUp(self):
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root)
        override.enable()
        self.addCleanup(override.disable)

        self.owner = CustomUser.objects.create_user(
            username='dup-owner', email='dup-owner@example.com', password='testpassword123'
        )
        self.friend = CustomUser.objects.create_user(
            username='dup-friend', email='dup-friend@example.com', password='testpassword123', public_profile=True
        )
        self.objects = build_rich_account(self.owner, self.friend)
        self.trip = self.objects['trip']
        self.client.force_authenticate(user=self.owner)

    def duplicate(self, user=None):
        if user:
            self.client.force_authenticate(user=user)
        return self.client.post(f'/api/collections/{self.trip.id}/duplicate/')

    def copy(self):
        response = self.duplicate()
        self.assertEqual(response.status_code, 201, response.content)
        return Collection.objects.get(id=response.json()['id'])

    def test_the_copy_is_a_private_unarchived_collection_with_the_same_dates(self):
        copy = self.copy()

        self.assertNotEqual(copy.id, self.trip.id)
        self.assertEqual(copy.name, 'Copy of Alps')
        self.assertEqual((copy.visibility, copy.is_archived, copy.user), ('private', False, self.owner))
        self.assertEqual((copy.type, copy.start_date, copy.end_date, copy.link, copy.description),
                         (self.trip.type, self.trip.start_date, self.trip.end_date, self.trip.link, self.trip.description))

    def test_the_copy_keeps_the_trips_timezone(self):
        self.assertEqual(self.copy().timezone, 'Europe/Paris')

    def test_places_are_linked_not_cloned(self):
        copy = self.copy()

        self.assertEqual(set(copy.locations.all()), {self.objects['hut'], self.objects['cafe']})
        self.assertEqual(Location.objects.filter(user=self.owner).count(), 3)

    def test_transport_lodging_notes_and_checklists_are_copied_with_their_files(self):
        copy = self.copy()

        train = Transportation.objects.get(collection=copy)
        self.assertEqual((train.name, train.start_code, train.end_code), ('TGV to Annecy', 'PAR', 'NCY'))
        self.assertNotEqual(train.id, self.objects['train'].id)
        self.assertEqual(ContentImage.objects.filter(object_id=train.id).count(), 1)
        self.assertEqual(ContentAttachment.objects.filter(object_id=train.id).count(), 1)
        inn = Lodging.objects.get(collection=copy)
        self.assertEqual((inn.name, inn.reservation_number), ('Chalet Mont-Blanc', 'CH-77'))
        self.assertEqual(ContentImage.objects.filter(object_id=inn.id).count(), 1)
        note = Note.objects.get(collection=copy)
        self.assertEqual((note.name, note.content), ('Packing', 'Layers'))
        checklist = Checklist.objects.get(collection=copy)
        self.assertEqual(sorted(i.name for i in checklist.checklistitem_set.all()), ['Gift', 'Passport'])

    def test_private_notes_and_checklist_items_stay_private(self):
        copy = self.copy()

        self.assertTrue(Note.objects.get(collection=copy).is_private)
        items = {i.name: i.is_private for i in Checklist.objects.get(collection=copy).checklistitem_set.all()}
        self.assertEqual(items, {'Passport': False, 'Gift': True})

    def test_the_cover_photo_is_copied_for_the_new_collection(self):
        copy = self.copy()

        self.assertIsNotNone(copy.primary_image)
        self.assertNotEqual(copy.primary_image_id, self.trip.primary_image_id)
        self.assertEqual(copy.primary_image.object_id, copy.id)

    def test_the_day_plan_is_copied_and_relinked_to_the_copied_records(self):
        copy = self.copy()

        self.assertEqual(CollectionItineraryDay.objects.filter(collection=copy).count(), 5)
        items = CollectionItineraryItem.objects.filter(collection=copy)
        self.assertEqual(items.count(), 6)
        train_row = items.get(content_type__model='transportation')
        self.assertEqual(train_row.object_id, Transportation.objects.get(collection=copy).id)
        self.assertEqual(train_row.day.collection_id, copy.id)
        hut_row = items.get(content_type__model='location', day__index=2)
        self.assertEqual(hut_row.object_id, self.objects['hut'].id)
        stay = items.get(content_type__model='lodging')
        self.assertEqual((stay.day.index, stay.span_end_index), (2, 4))
        self.assertIsNone(hut_row.logged_visit)

    def test_sharing_and_discussion_are_not_copied(self):
        copy = self.copy()

        self.assertFalse(copy.shared_with.exists())
        self.assertFalse(copy.guest_links.exists())
        self.assertFalse(CollectionInvite.objects.filter(collection=copy).exists())
        self.assertFalse(CollectionComment.objects.filter(collection=copy).exists())
        self.assertEqual(copy.comment_access, 'off')

    def test_the_original_is_untouched(self):
        before = (Transportation.objects.get(collection=self.trip).id, self.trip.itinerary_items.count())

        self.copy()
        self.trip.refresh_from_db()

        self.assertEqual(before, (Transportation.objects.get(collection=self.trip).id, self.trip.itinerary_items.count()))
        self.assertEqual(self.trip.name, 'Alps')

    def test_only_the_owner_can_duplicate(self):
        response = self.duplicate(user=self.friend)

        self.assertIn(response.status_code, (403, 404))
        self.assertEqual(Collection.objects.filter(name='Copy of Alps').count(), 0)

    def test_a_failure_part_way_leaves_no_half_built_copy(self):
        from unittest.mock import patch

        with patch('adventures.models.logistics.Note.objects.create', side_effect=RuntimeError('boom')):
            response = self.duplicate()

        self.assertEqual(response.status_code, 500)
        self.assertFalse(Collection.objects.filter(name='Copy of Alps').exists())
