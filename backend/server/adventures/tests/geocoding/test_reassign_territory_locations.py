from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from adventures.models import Location, Visit
from core.geo import make_point
from users.models import CustomUser
from worldtravel.models import City, Country, Region, VisitedCity, VisitedRegion


class ReassignTerritoryLocationsTests(TestCase):
    """Places geocoded before a territory was tied to its parent's region sit under the parent."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='territory-user', email='territory-user@example.com', password='testpassword123'
        )
        self.france = Country.objects.create(name='France', country_code='FR', coordinates=make_point(2.0, 46.0))
        self.guadeloupe = Country.objects.create(name='Guadeloupe', country_code='GP', coordinates=make_point(-61.58, 16.25))
        self.parent_region = Region.objects.create(id='FR-971', name='Guadeloupe', country=self.france, territory=self.guadeloupe)
        self.ordinary_region = Region.objects.create(id='FR-IDF', name='Ile-de-France', country=self.france)
        Region.objects.create(id='GP-01', name='Basse-Terre', country=self.guadeloupe, coordinates=make_point(-61.7, 16.0))
        self.pointe = Region.objects.create(id='GP-02', name='Pointe-à-Pitre', country=self.guadeloupe, coordinates=make_point(-61.53, 16.24))
        self.old_city = City.objects.create(id='FR-971-1', name='Pointe-à-Pitre', region=self.parent_region)
        self.new_city = City.objects.create(
            id='GP-02-1', name='Pointe-à-Pitre', region=self.pointe, coordinates=make_point(-61.53, 16.24)
        )

        now = timezone.now()
        self.visited = Location.objects.create(
            user=self.user, name='Fort', coordinates=make_point(-61.53, 16.24),
            country=self.france, region=self.parent_region, city=self.old_city,
        )
        Visit.objects.create(location=self.visited, start_date=now - timedelta(days=3), end_date=now - timedelta(days=2))
        VisitedRegion.objects.create(user=self.user, region=self.parent_region)
        VisitedCity.objects.create(user=self.user, city=self.old_city)
        self.elsewhere = Location.objects.create(
            user=self.user, name='Louvre', coordinates=make_point(2.33, 48.86),
            country=self.france, region=self.ordinary_region,
        )

    def _run(self, *args):
        out = StringIO()
        call_command('reassign_territory_locations', *args, stdout=out)
        return out.getvalue()

    def test_dry_run_writes_nothing(self):
        output = self._run()

        self.assertIn('Would move 1 location(s).', output)
        self.visited.refresh_from_db()
        self.assertEqual(self.visited.country, self.france)
        self.assertEqual(self.visited.region, self.parent_region)
        self.assertTrue(VisitedRegion.objects.filter(user=self.user, region=self.parent_region).exists())

    def test_apply_moves_the_place_onto_the_territory(self):
        output = self._run('--apply')

        self.assertIn('Moved 1 location(s).', output)
        self.visited.refresh_from_db()
        self.assertEqual(self.visited.country, self.guadeloupe)
        self.assertEqual(self.visited.region, self.pointe)
        self.assertEqual(self.visited.city, self.new_city)

    def test_apply_leaves_places_in_ordinary_regions_alone(self):
        self._run('--apply')

        self.elsewhere.refresh_from_db()
        self.assertEqual(self.elsewhere.country, self.france)
        self.assertEqual(self.elsewhere.region, self.ordinary_region)

    def test_visited_rows_follow_the_place(self):
        self._run('--apply')

        self.assertTrue(VisitedRegion.objects.filter(user=self.user, region=self.pointe).exists())
        self.assertTrue(VisitedCity.objects.filter(user=self.user, city=self.new_city).exists())
        self.assertFalse(VisitedRegion.objects.filter(user=self.user, region=self.parent_region).exists())
        self.assertFalse(VisitedCity.objects.filter(user=self.user, city=self.old_city).exists())

    def test_a_visited_row_the_user_has_no_place_for_is_kept(self):
        # It may be a mark the user made by hand.
        other = CustomUser.objects.create_user(username='other', email='other@example.com', password='testpassword123')
        VisitedRegion.objects.create(user=other, region=self.parent_region)

        self._run('--apply')

        self.assertTrue(VisitedRegion.objects.filter(user=other, region=self.parent_region).exists())

    def test_a_place_that_was_only_planned_is_moved_without_being_marked_visited(self):
        VisitedRegion.objects.all().delete()
        VisitedCity.objects.all().delete()
        Visit.objects.all().delete()

        self._run('--apply')

        self.visited.refresh_from_db()
        self.assertEqual(self.visited.country, self.guadeloupe)
        self.assertFalse(VisitedRegion.objects.exists())
        self.assertFalse(VisitedCity.objects.exists())

    def test_a_city_the_import_already_moved_onto_the_territory_is_kept(self):
        # After the world data merge the city sits in a region of the territory, and the place still points at it.
        moved = City.objects.create(id='FR-971-9', name='Gosier', region=self.pointe, coordinates=make_point(-61.49, 16.2))
        self.visited.city = moved
        self.visited.save(update_fields=['city'], _skip_geocode=True)

        self._run('--apply')

        self.visited.refresh_from_db()
        self.assertEqual(self.visited.city, moved)
        self.assertEqual(self.visited.region, self.pointe)
        self.assertEqual(self.visited.country, self.guadeloupe)

    def test_a_place_without_coordinates_gets_the_country_but_no_region(self):
        self.visited.coordinates = None
        self.visited.save(update_fields=['coordinates'], _skip_geocode=True)

        self._run('--apply')

        self.visited.refresh_from_db()
        self.assertEqual(self.visited.country, self.guadeloupe)
        self.assertIsNone(self.visited.region)
        self.assertIsNone(self.visited.city)

    def test_running_it_again_has_nothing_left_to_move(self):
        self._run('--apply')

        self.assertIn('Moved 0 location(s).', self._run('--apply'))
