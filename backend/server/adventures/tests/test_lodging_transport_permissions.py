from rest_framework.test import APITestCase

from adventures.models import Collection, Lodging, Transportation
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
