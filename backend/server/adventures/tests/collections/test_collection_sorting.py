"""Sorting the collections list: ascending means A to Z, earliest first, oldest first."""

from datetime import date, timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from adventures.models import Collection
from users.models import CustomUser


class CollectionSortingTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='sort-user', email='sort-user@example.com', password='testpassword123'
        )
        self.client.force_authenticate(user=self.user)
        now = timezone.now()
        spec = [
            # name, start, end, updated this many days ago
            ('beta', date(2026, 3, 1), date(2026, 3, 5), 3),
            ('Alpha', date(2026, 1, 1), date(2026, 1, 5), 1),
            ('gamma', date(2026, 2, 1), date(2026, 2, 5), 2),
            ('Delta (undated)', None, None, 4),
        ]
        for name, start, end, days_ago in spec:
            collection = Collection.objects.create(
                user=self.user, name=name, start_date=start, end_date=end, type='trip' if start else 'folder'
            )
            Collection.objects.filter(pk=collection.pk).update(updated_at=now - timedelta(days=days_ago))

    def names(self, **params):
        response = self.client.get('/api/collections/', params)
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        return [c['name'] for c in body.get('results', body)]

    def test_name_ascending_is_a_to_z_ignoring_case(self):
        self.assertEqual(
            self.names(order_by='name', order_direction='asc'),
            ['Alpha', 'beta', 'Delta (undated)', 'gamma'],
        )

    def test_name_descending_is_z_to_a(self):
        self.assertEqual(
            self.names(order_by='name', order_direction='desc'),
            ['gamma', 'Delta (undated)', 'beta', 'Alpha'],
        )

    def test_with_no_parameters_the_list_is_a_to_z(self):
        self.assertEqual(self.names(), ['Alpha', 'beta', 'Delta (undated)', 'gamma'])

    def test_start_date_ascending_is_earliest_first_with_undated_last(self):
        self.assertEqual(
            self.names(order_by='start_date', order_direction='asc'),
            ['Alpha', 'gamma', 'beta', 'Delta (undated)'],
        )

    def test_start_date_descending_is_latest_first_with_undated_last(self):
        self.assertEqual(
            self.names(order_by='start_date', order_direction='desc'),
            ['beta', 'gamma', 'Alpha', 'Delta (undated)'],
        )

    def test_updated_at_descending_is_most_recent_first(self):
        self.assertEqual(
            self.names(order_by='updated_at', order_direction='desc'),
            ['Alpha', 'gamma', 'beta', 'Delta (undated)'],
        )

    def test_updated_at_ascending_is_oldest_first(self):
        self.assertEqual(
            self.names(order_by='updated_at', order_direction='asc'),
            ['Delta (undated)', 'beta', 'gamma', 'Alpha'],
        )

    def test_an_unknown_field_falls_back_to_most_recently_updated(self):
        self.assertEqual(
            self.names(order_by='bogus', order_direction='desc'),
            ['Alpha', 'gamma', 'beta', 'Delta (undated)'],
        )

    def test_an_unknown_direction_falls_back_to_ascending(self):
        self.assertEqual(
            self.names(order_by='name', order_direction='sideways'),
            ['Alpha', 'beta', 'Delta (undated)', 'gamma'],
        )
