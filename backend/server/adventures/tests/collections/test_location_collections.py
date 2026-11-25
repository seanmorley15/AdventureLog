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

    def test_editor_who_does_not_own_the_place_cannot_unlink(self):
        self.client.force_authenticate(user=self.editor)
        self.place(self.trip_a)
        response = self.client.delete(self.url(self.trip_a))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(self.location.collections.filter(pk=self.trip_a.pk).exists())
        self.assertTrue(CollectionItineraryItem.objects.filter(collection=self.trip_a).exists())

    def test_place_owner_who_is_an_editor_can_unlink_their_own_place(self):
        own = Location.objects.create(user=self.editor, name='Mine')
        own.collections.add(self.trip_a)
        self.client.force_authenticate(user=self.editor)
        response = self.client.delete(f'/api/locations/{own.id}/collections/{self.trip_a.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(own.collections.filter(pk=self.trip_a.pk).exists())

    def test_editor_can_still_remove_the_placement_only(self):
        item = self.place(self.trip_a)
        self.client.force_authenticate(user=self.editor)
        response = self.client.delete(f'/api/collections/{self.trip_a.id}/itinerary-items/{item.id}/')
        self.assertIn(response.status_code, (200, 204))
        self.assertFalse(CollectionItineraryItem.objects.filter(pk=item.pk).exists())
        self.assertTrue(self.location.collections.filter(pk=self.trip_a.pk).exists())

    def test_can_unlink_is_owner_only_in_the_list(self):
        own = Location.objects.create(user=self.editor, name='Mine')
        own.collections.add(self.trip_a)
        self.client.force_authenticate(user=self.editor)
        row = next(r for r in self.client.get(self.url()).json() if r['name'] == 'Trip A')
        self.assertFalse(row['can_unlink'])
        own_rows = self.client.get(f'/api/locations/{own.id}/collections/').json()
        self.assertTrue(next(r for r in own_rows if r['name'] == 'Trip A')['can_unlink'])
        self.client.force_authenticate(user=self.owner)
        row = next(r for r in self.client.get(self.url()).json() if r['name'] == 'Trip A')
        self.assertTrue(row['can_unlink'])

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

    def test_patch_unlink_by_non_owner_editor_is_refused(self):
        self.client.force_authenticate(user=self.editor)
        self.place(self.trip_a)
        response = self.client.patch(
            f'/api/locations/{self.location.id}/', {'collections': []}, format='json'
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(self.location.collections.filter(pk=self.trip_a.pk).exists())
        self.assertTrue(CollectionItineraryItem.objects.filter(collection=self.trip_a).exists())

    def test_patch_unlink_by_collection_owner_removes_plan_rows(self):
        self.client.force_authenticate(user=self.owner)
        self.place(self.trip_a)
        response = self.client.patch(
            f'/api/locations/{self.location.id}/', {'collections': []}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.location.collections.filter(pk=self.trip_a.pk).exists())
        self.assertFalse(CollectionItineraryItem.objects.filter(collection=self.trip_a).exists())


class CreatorUnlinkTests(APITestCase):
    """A collaborator may take out of a trip what they added to it."""

    def setUp(self):
        self.owner = make_user('cu-owner')
        self.editor = make_user('cu-editor')
        self.other_editor = make_user('cu-other')
        self.trip = Collection.objects.create(user=self.owner, name='Trip')
        self.trip.shared_with.add(self.editor, self.other_editor)

    def create_in_trip(self, user, name='Added'):
        self.client.force_authenticate(user=user)
        response = self.client.post(
            '/api/locations/', {'name': name, 'collections': [str(self.trip.id)]}, format='json'
        )
        self.assertEqual(response.status_code, 201, response.content)
        return Location.objects.get(pk=response.json()['id'])

    def unlink(self, location, user):
        self.client.force_authenticate(user=user)
        return self.client.delete(f'/api/locations/{location.id}/collections/{self.trip.id}/')

    def test_created_by_is_set_on_create_inside_a_collection(self):
        location = self.create_in_trip(self.editor)
        self.assertEqual(location.user_id, self.owner.id)
        self.assertEqual(location.created_by_id, self.editor.id)

    def test_created_by_is_set_on_create_outside_a_collection(self):
        self.client.force_authenticate(user=self.editor)
        response = self.client.post('/api/locations/', {'name': 'Solo'}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Location.objects.get(pk=response.json()['id']).created_by_id, self.editor.id)

    def test_creator_editor_can_unlink_their_addition(self):
        location = self.create_in_trip(self.editor)
        self.assertEqual(self.unlink(location, self.editor).status_code, 200)
        self.assertFalse(location.collections.filter(pk=self.trip.pk).exists())

    def test_creator_cannot_unlink_someone_elses_place(self):
        theirs = self.create_in_trip(self.other_editor, 'Theirs')
        mine = self.create_in_trip(self.editor, 'Mine')
        self.assertEqual(self.unlink(theirs, self.editor).status_code, 403)
        self.assertTrue(theirs.collections.filter(pk=self.trip.pk).exists())
        self.assertEqual(self.unlink(mine, self.editor).status_code, 200)

    def test_creator_who_is_now_a_viewer_cannot_unlink(self):
        location = self.create_in_trip(self.editor)
        CollectionMember.objects.filter(collection=self.trip, user=self.editor).update(role='viewer')
        self.assertEqual(self.unlink(location, self.editor).status_code, 403)
        self.assertTrue(location.collections.filter(pk=self.trip.pk).exists())

    def test_creator_who_was_removed_from_the_trip_cannot_unlink(self):
        location = self.create_in_trip(self.editor)
        self.trip.shared_with.remove(self.editor)
        self.assertIn(self.unlink(location, self.editor).status_code, (403, 404))
        self.assertTrue(location.collections.filter(pk=self.trip.pk).exists())

    def test_owner_and_place_owner_are_unchanged(self):
        location = self.create_in_trip(self.editor)
        self.assertEqual(self.unlink(location, self.owner).status_code, 200)
        own = Location.objects.create(user=self.other_editor, name='Own')
        own.collections.add(self.trip)
        self.assertEqual(self.unlink(own, self.other_editor).status_code, 200)

    def test_can_unlink_in_the_list_follows_the_creator_rule(self):
        mine = self.create_in_trip(self.editor, 'Mine')
        theirs = self.create_in_trip(self.other_editor, 'Theirs')
        self.client.force_authenticate(user=self.editor)

        def row(location):
            rows = self.client.get(f'/api/locations/{location.id}/collections/').json()
            return next(r for r in rows if r['name'] == 'Trip')

        self.assertTrue(row(mine)['can_unlink'])
        self.assertFalse(row(theirs)['can_unlink'])

    def test_patch_dropping_the_collection_follows_the_creator_rule(self):
        mine = self.create_in_trip(self.editor, 'Mine')
        theirs = self.create_in_trip(self.other_editor, 'Theirs')
        self.client.force_authenticate(user=self.editor)
        self.assertEqual(
            self.client.patch(f'/api/locations/{theirs.id}/', {'collections': []}, format='json').status_code, 403
        )
        self.assertEqual(
            self.client.patch(f'/api/locations/{mine.id}/', {'collections': []}, format='json').status_code, 200
        )
        self.assertFalse(mine.collections.exists())

    def test_created_by_is_not_writable_and_is_shown_without_an_email(self):
        location = self.create_in_trip(self.editor)
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            f'/api/locations/{location.id}/', {'created_by': str(self.other_editor.uuid)}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        location.refresh_from_db()
        self.assertEqual(location.created_by_id, self.editor.id)
        body = self.client.get(f'/api/locations/{location.id}/').json()
        self.assertEqual(body['created_by']['uuid'], str(self.editor.uuid))
        self.assertEqual(body['created_by']['username'], self.editor.username)
        self.assertNotIn('email', body['created_by'])

    def test_created_by_is_null_for_old_places(self):
        old = Location.objects.create(user=self.owner, name='Old')
        self.client.force_authenticate(user=self.owner)
        self.assertIsNone(self.client.get(f'/api/locations/{old.id}/').json()['created_by'])

    def test_a_copy_has_no_creator_unless_the_copier_made_it(self):
        from adventures.services.locations.copy import copy_location

        location = self.create_in_trip(self.editor)
        self.assertIsNone(copy_location(location, self.other_editor).created_by_id)
