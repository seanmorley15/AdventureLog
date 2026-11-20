from django.test import TestCase

from core.geo import make_point
from users.models import CustomUser
from worldtravel.models import City, Country, Region, VisitedCity, VisitedRegion
from worldtravel.services import mark_cities_visited, mark_regions_visited


class MarkVisitedTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='mark-user', email='mark-user@example.com', password='testpassword123'
        )
        self.other = CustomUser.objects.create_user(
            username='mark-other', email='mark-other@example.com', password='testpassword123'
        )
        country = Country.objects.create(name='France', country_code='FR', coordinates=make_point(2.2, 46.2))
        self.idf = Region.objects.create(id='FR-IDF', name='Ile-de-France', country=country)
        self.bre = Region.objects.create(id='FR-BRE', name='Bretagne', country=country)
        self.paris = City.objects.create(id='FR-IDF-1', name='Paris', region=self.idf)
        self.brest = City.objects.create(id='FR-BRE-1', name='Brest', region=self.bre)

    def test_returns_and_creates_only_the_regions_not_yet_visited(self):
        VisitedRegion.objects.create(user=self.user, region=self.idf)

        new = mark_regions_visited(self.user.id, ['FR-IDF', 'FR-BRE'])

        self.assertEqual(new, {'FR-BRE'})
        self.assertEqual(VisitedRegion.objects.filter(user=self.user).count(), 2)

    def test_marking_twice_never_creates_duplicates(self):
        mark_regions_visited(self.user.id, ['FR-IDF', 'FR-IDF'])
        again = mark_regions_visited(self.user.id, ['FR-IDF'])

        self.assertEqual(again, set())
        self.assertEqual(VisitedRegion.objects.filter(user=self.user, region=self.idf).count(), 1)

    def test_dry_run_reports_without_writing(self):
        new = mark_cities_visited(self.user.id, ['FR-IDF-1'], dry_run=True)

        self.assertEqual(new, {'FR-IDF-1'})
        self.assertFalse(VisitedCity.objects.exists())

    def test_other_users_visits_do_not_count(self):
        VisitedCity.objects.create(user=self.other, city=self.paris)

        new = mark_cities_visited(self.user.id, ['FR-IDF-1', 'FR-BRE-1'])

        self.assertEqual(new, {'FR-IDF-1', 'FR-BRE-1'})
        self.assertEqual(VisitedCity.objects.filter(user=self.other).count(), 1)

    def test_accepts_any_iterable_and_empty_input(self):
        self.assertEqual(mark_cities_visited(self.user.id, iter(['FR-BRE-1'])), {'FR-BRE-1'})
        self.assertEqual(mark_cities_visited(self.user.id, []), set())
        self.assertEqual(VisitedCity.objects.filter(user=self.user).count(), 1)
