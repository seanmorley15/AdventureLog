"""How the locations list orders places with ``?ordering=``."""

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
        response = self.client.get('/api/locations/', params)
        self.assertEqual(response.status_code, 200, response.content)
        return [place['name'] for place in response.json()['results']]

    def test_name_is_plain_ascending_and_descending_ignoring_case(self):
        self.assertEqual(self.names(ordering='name'), ['Alpha', 'beta', 'gamma'])
        self.assertEqual(self.names(ordering='-name'), ['gamma', 'beta', 'Alpha'])

    def test_rating_is_plain_ascending_and_descending(self):
        self.assertEqual(self.names(ordering='rating'), ['beta', 'gamma', 'Alpha'])
        self.assertEqual(self.names(ordering='-rating'), ['Alpha', 'gamma', 'beta'])

    def test_updated_at_is_plain_ascending_and_descending(self):
        self.assertEqual(self.names(ordering='-updated_at'), ['Alpha', 'gamma', 'beta'])
        self.assertEqual(self.names(ordering='updated_at'), ['beta', 'gamma', 'Alpha'])

    def test_with_no_parameters_the_newest_places_come_first(self):
        self.assertEqual(self.names(), ['Alpha', 'gamma', 'beta'])

    def test_places_without_a_rating_come_last_instead_of_disappearing(self):
        Location.objects.create(user=self.user, name='unrated')
        self.assertEqual(self.names(ordering='-rating')[-1], 'unrated')
        self.assertEqual(self.names(ordering='rating')[-1], 'unrated')

    def test_an_unknown_ordering_is_a_validation_error(self):
        response = self.client.get('/api/locations/', {'ordering': 'secret_field'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('ordering', response.json()['fields'])
