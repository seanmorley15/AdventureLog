import uuid
from unittest.mock import patch

from rest_framework.test import APITestCase

from adventures.models import Category, Location
from users.models import CustomUser


@patch('adventures.views.location_view.reverse_geocode_service', return_value=None)
@patch('adventures.views.location_view.extract_google_place_details', return_value=({}, {}))
class LocationQuickAddCategoryTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='quick-add-user',
            email='quick-add-user@example.com',
            password='testpassword123',
        )
        self.client.force_authenticate(user=self.user)
        self.base_payload = {
            'name': 'Acadia National Park',
            'latitude': 44.3385,
            'longitude': -68.2733,
        }

    def test_quick_add_creates_category_from_client_generated_id(self, _details, _reverse):
        """The category dropdown used to send a fake UUID for new categories."""
        response = self.client.post(
            '/api/locations/quick-add/',
            {
                **self.base_payload,
                'category': {
                    'id': str(uuid.uuid4()),
                    'name': 'national_park',
                    'display_name': 'National Park',
                    'icon': '🏞️',
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.content)
        location = Location.objects.get(id=response.json()['id'])
        self.assertIsNotNone(location.category)
        self.assertEqual(location.category.name, 'national_park')
        self.assertEqual(location.category.display_name, 'National Park')
        self.assertEqual(location.category.icon, '🏞️')
        self.assertEqual(location.category.user, self.user)
        self.assertTrue(
            Category.objects.filter(user=self.user, name='national_park').exists()
        )

    def test_quick_add_creates_category_from_name_without_id(self, _details, _reverse):
        response = self.client.post(
            '/api/locations/quick-add/',
            {
                **self.base_payload,
                'category': {
                    'name': 'hiking',
                    'display_name': 'Hiking',
                    'icon': '🥾',
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.content)
        location = Location.objects.get(id=response.json()['id'])
        self.assertEqual(location.category.name, 'hiking')
        self.assertEqual(location.category.display_name, 'Hiking')

    def test_quick_add_uses_existing_category_by_id(self, _details, _reverse):
        category = Category.objects.create(
            user=self.user,
            name='museum',
            display_name='Museum',
            icon='🏛️',
        )

        response = self.client.post(
            '/api/locations/quick-add/',
            {
                **self.base_payload,
                'category': {
                    'id': str(category.id),
                    'name': 'ignored',
                    'display_name': 'Ignored',
                    'icon': '❓',
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.content)
        location = Location.objects.get(id=response.json()['id'])
        self.assertEqual(location.category_id, category.id)
        self.assertEqual(location.category.display_name, 'Museum')

    def test_quick_add_unknown_id_without_name_still_errors(self, _details, _reverse):
        response = self.client.post(
            '/api/locations/quick-add/',
            {
                **self.base_payload,
                'category': {'id': str(uuid.uuid4())},
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {'error': 'Category not found or inaccessible'},
        )
        self.assertFalse(Location.objects.filter(user=self.user).exists())
