from rest_framework.test import APITestCase

from adventures.models import Category, Location
from users.models import CustomUser


class LocationCategoryByNameTests(APITestCase):
    """A category sent by name finds the user's existing category (#1307)."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='explorer', email='explorer@example.com', password='testpassword'
        )
        self.client.force_authenticate(self.user)
        self.tour = Category.objects.create(
            user=self.user, name='tour', display_name='Tours & Activities', icon='🎟️'
        )

    def categories(self):
        return set(Category.objects.filter(user=self.user).values_list('name', flat=True))

    def create_location(self, category):
        response = self.client.post(
            '/api/locations/', {'name': 'Walking tour', 'category': category}, format='json'
        )
        self.assertEqual(response.status_code, 201, response.content)
        return Location.objects.get(id=response.json()['id'])

    def test_the_display_name_finds_the_existing_category(self):
        location = self.create_location({'name': 'Tours & Activities'})
        self.assertEqual(location.category, self.tour)
        self.assertNotIn('tours & activities', self.categories())

    def test_a_category_sent_the_way_the_ui_shows_it_is_not_duplicated(self):
        location = self.create_location(
            {'name': 'Tours & Activities', 'display_name': 'Tours & Activities', 'icon': '🎟️'}
        )
        self.assertEqual(location.category, self.tour)
        self.assertNotIn('tours & activities', self.categories())

    def test_the_name_finds_it_in_any_case(self):
        self.assertEqual(self.create_location({'name': 'TOUR'}).category, self.tour)
        self.assertEqual(self.create_location({'name': 'tours & activities'}).category, self.tour)
        self.assertNotIn('tours & activities', self.categories())

    def test_a_new_name_creates_a_category(self):
        location = self.create_location({'name': 'Food', 'display_name': 'Food', 'icon': '🍜'})
        self.assertEqual(location.category.name, 'food')
        self.assertEqual(location.category.display_name, 'Food')
        self.assertIn('food', self.categories())
