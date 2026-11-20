from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, APITestCase, force_authenticate

from adventures.models import Collection, CollectionMember
from adventures.permissions import ensure_can_add_to_collections
from users.models import CustomUser


class EnsureCanAddToCollectionsTests(APITestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='add-owner', email='add-owner@example.com', password='testpassword123'
        )
        self.editor = CustomUser.objects.create_user(
            username='add-editor', email='add-editor@example.com', password='testpassword123'
        )
        self.viewer = CustomUser.objects.create_user(
            username='add-viewer', email='add-viewer@example.com', password='testpassword123'
        )
        self.trip = Collection.objects.create(user=self.owner, name='Alps')
        self.trip.shared_with.add(self.editor, self.viewer)
        CollectionMember.objects.filter(collection=self.trip, user=self.viewer).update(role='viewer')

    def _request_as(self, user):
        raw = APIRequestFactory().get('/')
        force_authenticate(raw, user=user)
        request = Request(raw)
        request.user = user
        return request

    def test_owner_and_editor_may_add(self):
        for user in (self.owner, self.editor):
            with self.subTest(user=user.username):
                ensure_can_add_to_collections(self._request_as(user), [self.trip], 'location')

    def test_viewer_is_refused_and_the_message_names_the_record_kind(self):
        for noun in ('location', 'lodging'):
            with self.subTest(noun=noun):
                with self.assertRaises(PermissionDenied) as ctx:
                    ensure_can_add_to_collections(self._request_as(self.viewer), [self.trip], noun)
                self.assertEqual(
                    str(ctx.exception.detail),
                    f"You don't have permission to add {noun} to collection 'Alps'",
                )

    def test_one_refused_collection_refuses_the_whole_request(self):
        other = Collection.objects.create(user=self.owner, name='Pyrenees')
        with self.assertRaises(PermissionDenied):
            ensure_can_add_to_collections(self._request_as(self.editor), [self.trip, other], 'location')

    def test_creating_a_location_in_a_viewer_collection_is_refused_by_the_api(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.post(
            '/api/locations/', {'name': 'Hut', 'collections': [str(self.trip.id)]}, format='json'
        )

        self.assertEqual(response.status_code, 403, response.content)
