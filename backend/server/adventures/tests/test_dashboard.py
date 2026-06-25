from datetime import date, timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from adventures.models import Collection, Location, Visit
from users.models import CustomUser
from worldtravel.models import City, Country, Region


class DashboardAPITestCase(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='dashboard-user',
            email='dashboard-user@example.com',
            password='testpassword123',
        )
        self.country = Country.objects.create(name='France', country_code='FR')
        self.region = Region.objects.create(id='FR-75', name='Paris Region', country=self.country)
        self.city = City.objects.create(id='FR-75-paris', name='Paris City', region=self.region)

    def test_dashboard_requires_authentication(self):
        response = self.client.get('/api/stats/dashboard/')
        self.assertIn(response.status_code, [401, 403])

    def test_dashboard_returns_expected_shape_for_empty_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/stats/dashboard/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn('stats', data)
        self.assertIn('recent_locations', data)
        self.assertIn('upcoming_trips', data)
        self.assertIn('active_trip', data)
        self.assertIn('upcoming_events', data)
        self.assertIn('invite_count', data)

        self.assertEqual(data['stats']['location_count'], 0)
        self.assertEqual(data['recent_locations'], [])
        self.assertEqual(data['upcoming_trips'], [])
        self.assertIsNone(data['active_trip'])
        self.assertEqual(data['invite_count'], 0)

    def test_dashboard_includes_recent_visited_locations(self):
        location = Location.objects.create(
            user=self.user,
            name='Eiffel Tower',
            location='Paris, France',
            country=self.country,
            region=self.region,
            city=self.city,
        )
        Visit.objects.create(
            location=location,
            start_date=timezone.now() - timedelta(days=7),
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/stats/dashboard/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['recent_locations']), 1)
        self.assertEqual(data['recent_locations'][0]['name'], 'Eiffel Tower')
        self.assertEqual(data['stats']['visited_location_count'], 1)

    def test_dashboard_includes_upcoming_trip(self):
        Collection.objects.create(
            user=self.user,
            name='Summer Trip',
            start_date=date.today() + timedelta(days=14),
            end_date=date.today() + timedelta(days=21),
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/stats/dashboard/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['upcoming_trips']), 1)
        self.assertEqual(data['upcoming_trips'][0]['name'], 'Summer Trip')
        self.assertEqual(data['stats']['trips_count'], 1)

    def test_dashboard_omits_activities_by_category(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/stats/dashboard/')

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('activities_by_category', response.json()['stats'])

    def test_counts_endpoint_still_includes_activities_by_category(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/stats/counts/{self.user.username}/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('activities_by_category', response.json())
