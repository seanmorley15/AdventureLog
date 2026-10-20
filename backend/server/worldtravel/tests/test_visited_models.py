from django.core.exceptions import ValidationError
from django.test import TestCase

from core.geo import make_point
from users.models import CustomUser
from worldtravel.models import City, Country, Region, VisitedCity, VisitedRegion


class VisitedModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='visited-user', email='visited-user@example.com', password='testpassword123'
        )
        country = Country.objects.create(name='France', country_code='FR', coordinates=make_point(2.2, 46.2))
        self.region = Region.objects.create(id='FR-IDF', name='Ile-de-France', country=country)
        self.city = City.objects.create(id='FR-IDF-1', name='Paris', region=self.region)

    def test_saving_an_existing_visited_region_again_is_allowed(self):
        visited = VisitedRegion.objects.create(user=self.user, region=self.region)

        visited.save()

        self.assertEqual(VisitedRegion.objects.filter(user=self.user, region=self.region).count(), 1)

    def test_duplicate_visited_region_is_still_rejected(self):
        VisitedRegion.objects.create(user=self.user, region=self.region)

        with self.assertRaises(ValidationError):
            VisitedRegion.objects.create(user=self.user, region=self.region)

    def test_saving_an_existing_visited_city_again_is_allowed(self):
        visited = VisitedCity.objects.create(user=self.user, city=self.city)

        visited.save()

        self.assertEqual(VisitedCity.objects.filter(user=self.user, city=self.city).count(), 1)

    def test_duplicate_visited_city_is_still_rejected(self):
        VisitedCity.objects.create(user=self.user, city=self.city)

        with self.assertRaises(ValidationError):
            VisitedCity.objects.create(user=self.user, city=self.city)
