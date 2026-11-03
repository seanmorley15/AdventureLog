from rest_framework.test import APITestCase

from adventures.models import Category, Location
from users.models import CustomUser


class LocationCategoryLookupTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='category-user',
            email='category-user@example.com',
            password='testpassword123',
        )
        self.client.force_authenticate(user=self.user)
        self.category = Category.objects.create(
            user=self.user,
            name='tour',
            display_name='Tours & Activities',
            icon='🎟️',
        )

    def test_create_matches_existing_category_by_display_name(self):
        response = self.client.post(
            '/api/locations/',
            {
                'name': 'Walking Tour',
                'category': {
                    'name': 'Tours & Activities',
                    'display_name': 'Tours & Activities',
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.content)
        location = Location.objects.get(id=response.json()['id'])
        self.assertEqual(location.category_id, self.category.id)
        self.assertFalse(
            Category.objects.filter(user=self.user, name='tours & activities').exists()
        )
