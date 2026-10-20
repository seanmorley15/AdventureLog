from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APITestCase

from adventures.models import (
    Collection,
    CollectionItineraryItem,
    CollectionMember,
    Location,
)
from users.models import CustomUser


def make_user(name):
    return CustomUser.objects.create_user(
        username=name, email=f'{name}@example.com', password='testpassword123'
    )


class LocationCollectionMembershipTests(APITestCase):
    def setUp(self):
        self.owner = make_user('lc-owner')
        self.editor = make_user('lc-editor')
        self.viewer = make_user('lc-viewer')
        self.outsider = make_user('lc-outsider')

        self.trip_a = Collection.objects.create(user=self.owner, name='Trip A')
        self.trip_b = Collection.objects.create(user=self.owner, name='Trip B')
        self.trip_a.shared_with.add(self.editor, self.viewer)
        CollectionMember.objects.filter(collection=self.trip_a, user=self.viewer).update(role='viewer')

        self.location = Location.objects.create(user=self.owner, name='Place')
        self.location.collections.add(self.trip_a, self.trip_b)

    def url(self, collection=None):
        base = f'/api/locations/{self.location.id}/collections/'
        return f'{base}{collection.id}/' if collection else base

    def place(self, collection):
        return CollectionItineraryItem.objects.create(
            collection=collection,
            content_type=ContentType.objects.get_for_model(Location),
            object_id=self.location.id,
            order=0,
            is_global=True,
        )

    def test_owner_unlinks_one_collection_and_keeps_the_other(self):
        self.client.force_authenticate(user=self.owner)
        self.place(self.trip_a)
        response = self.client.delete(self.url(self.trip_a))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['removed_placements'], 1)
        self.assertEqual(list(self.location.collections.all()), [self.trip_b])
        self.assertFalse(CollectionItineraryItem.objects.filter(collection=self.trip_a).exists())

    def test_unlink_is_idempotent(self):
        self.client.force_authenticate(user=self.owner)
        self.assertEqual(self.client.delete(self.url(self.trip_a)).status_code, 200)
        self.assertEqual(self.client.delete(self.url(self.trip_a)).status_code, 200)

    def test_link_is_idempotent(self):
        self.location.collections.remove(self.trip_b)
        self.client.force_authenticate(user=self.owner)
        self.assertEqual(self.client.post(self.url(self.trip_b)).status_code, 200)
        self.assertEqual(self.client.post(self.url(self.trip_b)).status_code, 200)
        self.assertEqual(self.location.collections.count(), 2)

    def test_editor_unlink_removes_plan_rows(self):
        self.client.force_authenticate(user=self.editor)
        self.place(self.trip_a)
        response = self.client.delete(self.url(self.trip_a))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CollectionItineraryItem.objects.filter(collection=self.trip_a).exists())

    def test_viewer_cannot_unlink(self):
        self.client.force_authenticate(user=self.viewer)
        response = self.client.delete(self.url(self.trip_a))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(self.location.collections.filter(pk=self.trip_a.pk).exists())

    def test_outsider_cannot_see_collection(self):
        self.client.force_authenticate(user=self.outsider)
        self.assertIn(self.client.delete(self.url(self.trip_b)).status_code, (403, 404))
        self.assertTrue(self.location.collections.filter(pk=self.trip_b.pk).exists())

    def test_viewer_cannot_link(self):
        self.client.force_authenticate(user=self.viewer)
        response = self.client.post(self.url(self.trip_a))
        self.assertEqual(response.status_code, 403)

    def test_list_reports_linked_first_with_placements_and_permissions(self):
        self.place(self.trip_b)
        self.client.force_authenticate(user=self.owner)
        rows = self.client.get(self.url()).json()
        self.assertEqual({r['name'] for r in rows}, {'Trip A', 'Trip B'})
        self.assertTrue(all(r['is_linked'] for r in rows))
        by_name = {r['name']: r for r in rows}
        self.assertEqual(by_name['Trip B']['placements'], [{'day_index': None, 'is_global': True}])
        self.assertEqual(by_name['Trip A']['placements'], [])

    def test_list_includes_unlinked_editable_collections_and_search(self):
        self.location.collections.remove(self.trip_b)
        self.client.force_authenticate(user=self.owner)
        rows = self.client.get(self.url()).json()
        self.assertEqual([r['name'] for r in rows], ['Trip A', 'Trip B'])
        self.assertFalse(rows[1]['is_linked'])
        self.assertTrue(rows[1]['can_link'])
        filtered = self.client.get(self.url(), {'q': 'trip b'}).json()
        self.assertEqual([r['name'] for r in filtered], ['Trip B'])

    def test_list_marks_viewer_role_as_not_linkable(self):
        self.client.force_authenticate(user=self.viewer)
        rows = self.client.get(self.url()).json()
        row = next(r for r in rows if r['name'] == 'Trip A')
        self.assertFalse(row['can_link'])
        self.assertFalse(row['can_unlink'])

    def test_patch_keeps_links_the_requester_cannot_open(self):
        self.client.force_authenticate(user=self.editor)
        response = self.client.patch(
            f'/api/locations/{self.location.id}/',
            {'collections': [str(self.trip_a.id)]},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.location.collections.filter(pk=self.trip_b.pk).exists())

    def test_patch_unlink_by_editor_removes_plan_rows(self):
        self.client.force_authenticate(user=self.editor)
        self.place(self.trip_a)
        response = self.client.patch(
            f'/api/locations/{self.location.id}/', {'collections': []}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.location.collections.filter(pk=self.trip_a.pk).exists())
        self.assertFalse(CollectionItineraryItem.objects.filter(collection=self.trip_a).exists())
