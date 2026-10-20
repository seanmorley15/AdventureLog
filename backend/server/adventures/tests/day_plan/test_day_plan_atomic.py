from datetime import date
from unittest.mock import patch

from rest_framework.test import APITestCase

from adventures.models import Collection, CollectionItineraryDay
from adventures.services import day_plan
from adventures.services.day_plan import conversion
from users.models import CustomUser


class DayPlanWritesAreAllOrNothingTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='atomic-user', email='atomic-user@example.com', password='testpassword123'
        )
        self.client.force_authenticate(user=self.user)

    def test_build_days_leaves_no_days_behind_when_it_fails_midway(self):
        trip = Collection.objects.create(
            user=self.user, name='Trip', type='trip', start_date=date(2026, 6, 1), end_date=date(2026, 6, 3)
        )

        with patch.object(conversion, 'sync_projection', side_effect=RuntimeError('boom')):
            with self.assertRaises(RuntimeError):
                day_plan.build_days(trip, 3)

        self.assertFalse(CollectionItineraryDay.objects.filter(collection=trip).exists())

    def test_convert_collection_leaves_no_days_behind_when_it_fails_midway(self):
        trip = Collection.objects.create(
            user=self.user, name='Trip', type='trip', start_date=date(2026, 6, 1), end_date=date(2026, 6, 3)
        )

        real_build = conversion._build_day_plan

        def build_then_fail(collection, count, reg):
            real_build(collection, count, reg)
            raise RuntimeError('boom')

        with patch.object(conversion, '_build_day_plan', side_effect=build_then_fail):
            with self.assertRaises(RuntimeError):
                day_plan.convert_collection(trip)

        self.assertFalse(CollectionItineraryDay.objects.filter(collection=trip).exists())

    def test_creating_a_trip_does_not_keep_the_collection_when_its_days_fail(self):
        with patch.object(conversion, 'sync_projection', side_effect=RuntimeError('boom')):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    '/api/collections/',
                    {'name': 'Doomed trip', 'type': 'trip', 'start_date': '2026-06-01', 'day_count': 3},
                    format='json',
                )

        self.assertFalse(Collection.objects.filter(name='Doomed trip').exists())

    def test_creating_a_trip_with_days_still_works(self):
        response = self.client.post(
            '/api/collections/',
            {'name': 'Fine trip', 'type': 'trip', 'start_date': '2026-06-01', 'day_count': 3},
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.content)
        trip = Collection.objects.get(name='Fine trip')
        self.assertEqual(CollectionItineraryDay.objects.filter(collection=trip, index__isnull=False).count(), 3)
