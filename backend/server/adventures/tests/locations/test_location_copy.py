"""Copying a place: what comes along, what stays behind, and who may do it."""

import shutil
import tempfile

from django.test import override_settings
from rest_framework.test import APITestCase

from adventures.models import Category, Collection, CollectionMember, ContentAttachment, ContentImage, Location, Visit
from adventures.tests.factories import build_rich_account
from users.models import CustomUser


class CopyLocationTests(APITestCase):
    def setUp(self):
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root)
        override.enable()
        self.addCleanup(override.disable)

        self.owner = CustomUser.objects.create_user(
            username='copy-owner', email='copy-owner@example.com', password='testpassword123'
        )
        self.friend = CustomUser.objects.create_user(
            username='copy-friend', email='copy-friend@example.com', password='testpassword123', public_profile=True
        )
        self.stranger = CustomUser.objects.create_user(
            username='copy-stranger', email='copy-stranger@example.com', password='testpassword123'
        )
        self.objects = build_rich_account(self.owner, self.friend)
        self.hut = self.objects['hut']
        self.client.force_authenticate(user=self.owner)

    def copy(self, user=None, **data):
        if user:
            self.client.force_authenticate(user=user)
        return self.client.post(f'/api/locations/{self.hut.id}/duplicate/', data, format='json')

    def test_the_copy_is_a_private_place_with_the_same_details(self):
        response = self.copy()

        self.assertEqual(response.status_code, 201, response.content)
        new = Location.objects.get(id=response.json()['id'])
        self.assertNotEqual(new.id, self.hut.id)
        self.assertEqual(new.name, 'Copy of Refuge du Goûter')
        self.assertEqual((new.user, new.is_public), (self.owner, False))
        self.assertEqual((new.description, new.rating, new.link, new.location, new.tags),
                         (self.hut.description, self.hut.rating, self.hut.link, self.hut.location, self.hut.tags))
        self.assertEqual((str(new.price.amount), new.price.currency.code), ('120.00', 'EUR'))
        self.assertEqual((new.city_id, new.region_id, new.country_id),
                         (self.hut.city_id, self.hut.region_id, self.hut.country_id))
        self.assertEqual((new.coordinates.x, new.coordinates.y), (self.hut.coordinates.x, self.hut.coordinates.y))

    def test_collections_visits_and_attachments_stay_with_the_original(self):
        new = Location.objects.get(id=self.copy().json()['id'])

        self.assertFalse(new.collections.exists())
        self.assertFalse(Visit.objects.filter(location=new).exists())
        self.assertFalse(ContentAttachment.objects.filter(object_id=new.id).exists())

    def test_photos_are_copied_as_independent_files_and_immich_photos_are_referenced(self):
        new = Location.objects.get(id=self.copy().json()['id'])

        originals = ContentImage.objects.filter(object_id=self.hut.id)
        copies = ContentImage.objects.filter(object_id=new.id)
        self.assertEqual(copies.count(), originals.count())
        stored = [c for c in copies if c.image]
        self.assertEqual(len(stored), originals.exclude(image='').exclude(image__isnull=True).count())
        for photo in stored:
            self.assertNotIn(photo.image.name, [o.image.name for o in originals if o.image])
        self.assertEqual([c.immich_id for c in copies if c.immich_id], ['immich-1'])
        self.assertEqual(sorted(c.is_primary for c in copies), sorted(o.is_primary for o in originals))

    def test_the_category_is_reused_or_created_for_the_copier(self):
        self.client.force_authenticate(user=self.owner)
        Category.objects.filter(user=self.owner, name='food').update(display_name='Kept as is')

        new = Location.objects.get(id=self.copy().json()['id'])

        self.assertEqual(Category.objects.filter(user=self.owner, name='food').count(), 1)
        self.assertEqual(new.category.display_name, 'Kept as is')

    def test_a_collection_member_can_copy_a_shared_place_into_their_own_account(self):
        self.objects['trip'].shared_with.add(self.stranger)
        CollectionMember.objects.filter(collection=self.objects['trip'], user=self.stranger).update(role='editor')

        response = self.copy(user=self.stranger)

        self.assertEqual(response.status_code, 201, response.content)
        new = Location.objects.get(id=response.json()['id'])
        self.assertEqual(new.user, self.stranger)
        self.assertEqual(Category.objects.get(user=self.stranger, name='food').icon, '🍜')

    def test_naming_a_collection_links_the_copy_to_only_that_collection(self):
        target = self.objects['folder']

        new = Location.objects.get(id=self.copy(collection_id=str(target.id)).json()['id'])

        self.assertEqual(list(new.collections.all()), [target])

    def test_an_unknown_collection_is_a_404_and_nothing_is_created(self):
        before = Location.objects.count()

        response = self.copy(collection_id='11111111-1111-1111-1111-111111111111')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Location.objects.count(), before)

    def test_a_collection_the_user_cannot_edit_is_a_403_and_nothing_is_created(self):
        theirs = Collection.objects.create(user=self.stranger, name='Not yours')
        before = Location.objects.count()

        response = self.copy(collection_id=str(theirs.id))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Location.objects.count(), before)

    def test_someone_who_cannot_read_the_place_cannot_copy_it(self):
        private = Location.objects.create(user=self.owner, name='Private spot')

        self.client.force_authenticate(user=self.stranger)
        response = self.client.post(f'/api/locations/{private.id}/duplicate/', {}, format='json')

        self.assertIn(response.status_code, (403, 404))
        self.assertFalse(Location.objects.filter(name='Copy of Private spot').exists())
