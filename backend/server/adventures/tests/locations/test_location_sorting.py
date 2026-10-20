"""How the locations list orders places. The page relies on 'asc' for updated_at meaning newest first."""

from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from adventures.models import Location
from users.models import CustomUser


class LocationSortingTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='locsort-user', email='locsort-user@example.com', password='testpassword123'
        )
        self.client.force_authenticate(user=self.user)
        now = timezone.now()
        for name, days_ago, rating in (('beta', 3, 2.0), ('Alpha', 1, 5.0), ('gamma', 2, 3.5)):
            place = Location.objects.create(user=self.user, name=name, rating=rating)
            Location.objects.filter(pk=place.pk).update(updated_at=now - timedelta(days=days_ago))

    def names(self, **params):
        response = self.client.get('/api/locations/filtered/', {'types': 'all', **params})
        self.assertEqual(response.status_code, 200, response.content)
        return [place['name'] for place in response.json()['results']]

    def test_name_is_plain_ascending_and_descending_ignoring_case(self):
        self.assertEqual(self.names(order_by='name', order_direction='asc'), ['Alpha', 'beta', 'gamma'])
        self.assertEqual(self.names(order_by='name', order_direction='desc'), ['gamma', 'beta', 'Alpha'])

    def test_rating_is_plain_ascending_and_descending(self):
        self.assertEqual(self.names(order_by='rating', order_direction='asc'), ['beta', 'gamma', 'Alpha'])
        self.assertEqual(self.names(order_by='rating', order_direction='desc'), ['Alpha', 'gamma', 'beta'])

    def test_updated_at_ascending_is_newest_first_which_is_the_pages_default_view(self):
        self.assertEqual(self.names(order_by='updated_at', order_direction='asc'), ['Alpha', 'gamma', 'beta'])
        self.assertEqual(self.names(order_by='updated_at', order_direction='desc'), ['beta', 'gamma', 'Alpha'])

    def test_with_no_parameters_the_newest_places_come_first(self):
        self.assertEqual(self.names(), ['Alpha', 'gamma', 'beta'])
