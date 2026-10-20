from rest_framework.test import APITestCase

from adventures.models import Checklist, Collection, Lodging, Note, Transportation
from users.models import CustomUser


class LodgingPermissionTests(APITestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='lodging-owner',
            email='lodging-owner@example.com',
            password='testpassword123',
        )
        self.other = CustomUser.objects.create_user(
            username='lodging-other',
            email='lodging-other@example.com',
            password='testpassword123',
        )
        self.collection = Collection.objects.create(user=self.owner, name='Owner Trip')

    def test_anonymous_list_is_forbidden(self):
        response = self.client.get('/api/lodging/')
        self.assertEqual(response.status_code, 403)

    def test_owner_can_create_and_other_user_cannot_list_it(self):
        self.client.force_authenticate(user=self.owner)
        created = self.client.post('/api/lodging/', {'name': 'Left Bank Hotel'}, format='json')
        self.assertEqual(created.status_code, 201)
        self.assertEqual(Lodging.objects.get().user, self.owner)

        self.client.force_authenticate(user=self.other)
        listed = self.client.get('/api/lodging/')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json(), [])

    def test_other_user_cannot_create_in_owner_collection(self):
        self.client.force_authenticate(user=self.other)
        response = self.client.post(
            '/api/lodging/',
            {'name': 'Sneaky Stay', 'collection': str(self.collection.id)},
            format='json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Lodging.objects.filter(name='Sneaky Stay').exists())


class TransportationPermissionTests(APITestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='transport-owner',
            email='transport-owner@example.com',
            password='testpassword123',
        )
        self.other = CustomUser.objects.create_user(
            username='transport-other',
            email='transport-other@example.com',
            password='testpassword123',
        )
        self.collection = Collection.objects.create(user=self.owner, name='Owner Trip')

    def test_anonymous_list_is_forbidden(self):
        response = self.client.get('/api/transportations/')
        self.assertEqual(response.status_code, 403)

    def test_owner_can_create_and_other_user_cannot_list_it(self):
        self.client.force_authenticate(user=self.owner)
        created = self.client.post(
            '/api/transportations/',
            {'name': 'Train to Lyon', 'type': 'train'},
            format='json',
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(Transportation.objects.get().user, self.owner)

        self.client.force_authenticate(user=self.other)
        listed = self.client.get('/api/transportations/')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json(), [])

    def test_other_user_cannot_create_in_owner_collection(self):
        self.client.force_authenticate(user=self.other)
        response = self.client.post(
            '/api/transportations/',
            {
                'name': 'Sneaky Flight',
                'type': 'plane',
                'collection': str(self.collection.id),
            },
            format='json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Transportation.objects.filter(name='Sneaky Flight').exists())


class CollectionReassignmentMixin:
    """
    A collection editor may change a shared record's fields but not move it
    between collections; PUT and PATCH follow the same rules.
    """

    url = None
    model = None
    create_kwargs = {}
    put_payload = {}

    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username=f'{self.url}-owner', email=f'{self.url}-owner@example.com', password='testpassword123'
        )
        self.editor = CustomUser.objects.create_user(
            username=f'{self.url}-editor', email=f'{self.url}-editor@example.com', password='testpassword123'
        )
        self.collection = Collection.objects.create(user=self.owner, name='Owner Trip')
        self.collection.shared_with.add(self.editor)
        self.owner_other_collection = Collection.objects.create(user=self.owner, name='Owner Second Trip')
        self.editor_collection = Collection.objects.create(user=self.editor, name='Editor Trip')
        self.record = self.model.objects.create(
            user=self.owner, collection=self.collection, name='Shared record', **self.create_kwargs
        )
        self.detail = f'/api/{self.url}/{self.record.id}/'

    def test_editor_can_patch_fields_without_sending_collection(self):
        self.client.force_authenticate(user=self.editor)
        response = self.client.patch(self.detail, {'name': 'Renamed by editor'}, format='json')

        self.assertEqual(response.status_code, 200, response.content)
        self.record.refresh_from_db()
        self.assertEqual(self.record.name, 'Renamed by editor')
        self.assertEqual(self.record.collection, self.collection)

    def test_editor_put_cannot_move_record_into_their_own_collection(self):
        self.client.force_authenticate(user=self.editor)
        payload = {**self.put_payload, 'name': 'Stolen', 'collection': str(self.editor_collection.id)}
        response = self.client.put(self.detail, payload, format='json')

        self.assertEqual(response.status_code, 403, response.content)
        self.record.refresh_from_db()
        self.assertEqual(self.record.collection, self.collection)
        self.assertEqual(self.record.name, 'Shared record')

    def test_editor_patch_cannot_move_record_into_their_own_collection(self):
        self.client.force_authenticate(user=self.editor)
        response = self.client.patch(self.detail, {'collection': str(self.editor_collection.id)}, format='json')

        self.assertEqual(response.status_code, 403, response.content)
        self.record.refresh_from_db()
        self.assertEqual(self.record.collection, self.collection)

    def test_editor_cannot_remove_record_from_collection(self):
        self.client.force_authenticate(user=self.editor)
        for method, payload in (
            (self.client.patch, {'collection': None}),
            (self.client.put, {**self.put_payload, 'name': 'Detached', 'collection': None}),
        ):
            response = method(self.detail, payload, format='json')
            self.assertEqual(response.status_code, 403, response.content)
        self.record.refresh_from_db()
        self.assertEqual(self.record.collection, self.collection)

    def test_owner_can_move_record_between_own_collections_with_put_or_patch(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(self.detail, {'collection': str(self.owner_other_collection.id)}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.record.refresh_from_db()
        self.assertEqual(self.record.collection, self.owner_other_collection)

        payload = {**self.put_payload, 'name': 'Back again', 'collection': str(self.collection.id)}
        response = self.client.put(self.detail, payload, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.record.refresh_from_db()
        self.assertEqual(self.record.collection, self.collection)


class LodgingCollectionReassignmentTests(CollectionReassignmentMixin, APITestCase):
    url = 'lodging'
    model = Lodging


class TransportationCollectionReassignmentTests(CollectionReassignmentMixin, APITestCase):
    url = 'transportations'
    model = Transportation
    create_kwargs = {'type': 'train'}
    put_payload = {'type': 'train'}


class NoteCollectionReassignmentTests(CollectionReassignmentMixin, APITestCase):
    url = 'notes'
    model = Note


class ChecklistCollectionReassignmentTests(CollectionReassignmentMixin, APITestCase):
    url = 'checklists'
    model = Checklist
    put_payload = {'items': []}
