from io import StringIO

from django.test import SimpleTestCase, TestCase

from adventures.models import Location
from core.geo import make_point
from users.models import CustomUser
from worldtravel.management.commands.download_countries import Command
from worldtravel.models import City, CityAlias, Country, Region, VisitedCity
from worldtravel.services import resolve_city
from worldtravel.territories import pair_cities


class PairCitiesTests(SimpleTestCase):
    def test_cities_with_the_same_name_once_on_each_side_are_paired(self):
        pairs = pair_cities([('a1', 'San Juan'), ('a2', 'Ponce')], [('b1', 'Ponce'), ('b2', 'San Juan')])

        self.assertEqual(sorted(pairs), [('a1', 'b2'), ('a2', 'b1')])

    def test_accents_and_case_do_not_matter(self):
        self.assertEqual(pair_cities([('a', 'Añasco')], [('b', 'anasco')]), [('a', 'b')])

    def test_a_name_that_appears_twice_on_either_side_is_not_paired(self):
        self.assertEqual(pair_cities([('a1', 'Ponce'), ('a2', 'Ponce')], [('b', 'Ponce')]), [])
        self.assertEqual(pair_cities([('a', 'Ponce')], [('b1', 'Ponce'), ('b2', 'Ponce')]), [])

    def test_cities_with_no_partner_or_no_name_are_not_paired(self):
        self.assertEqual(pair_cities([('a', 'Bayamón'), ('c', '')], [('b', 'Ponce'), ('d', '')]), [])


class MergeTerritoryCitiesTests(SimpleTestCase):
    """The importer step that keeps a territory's cities on the territory. Works on the temporary tables only."""

    def setUp(self):
        self.command = Command()
        self.command.stdout = StringIO()

    def _run(self, countries, regions, cities):
        with self.command._temp_db() as conn:
            for code, name, lon, lat in countries:
                conn.execute(
                    'INSERT INTO temp_countries (country_code, name, native, longitude, latitude) VALUES (?, ?, ?, ?, ?)',
                    (code, name, '', lon, lat),
                )
            for region_id, name, region_type, code, lon, lat in regions:
                conn.execute(
                    'INSERT INTO temp_regions (id, name, native, type, country_code, longitude, latitude) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (region_id, name, '', region_type, code, lon, lat),
                )
            for city_id, name, region_id, lon, lat in cities:
                conn.execute(
                    'INSERT INTO temp_cities (id, name, region_id, longitude, latitude) VALUES (?, ?, ?, ?, ?)',
                    (city_id, name, region_id, lon, lat),
                )
            self.command._merge_territory_cities(conn)
            where = dict(conn.execute('SELECT id, region_id FROM temp_cities').fetchall())
            aliases = dict(conn.execute('SELECT old_id, new_id FROM temp_city_aliases').fetchall())
            return where, aliases

    COUNTRIES = [('US', 'United States', -97.0, 38.0), ('PR', 'Puerto Rico', -66.5, 18.25)]
    REGIONS = [
        ('US-AL', 'Alabama', 'state', 'US', -86.8, 32.8),
        ('US-GA', 'Georgia', 'state', 'US', -83.6, 33.0),
        ('US-AK', 'Alaska', 'state', 'US', -149.5, 64.2),
        ('US-PR', 'Puerto Rico', 'outlying area', 'US', -66.5, 18.25),
        ('PR-SJ', 'San Juan', 'municipality', 'PR', -66.1, 18.45),
        ('PR-PO', 'Ponce', 'municipality', 'PR', -66.6, 18.0),
    ]

    def test_a_city_listed_on_both_sides_is_dropped_from_the_parent_and_aliased(self):
        where, aliases = self._run(self.COUNTRIES, self.REGIONS, [
            ('US-PR-1', 'San Juan', 'US-PR', -66.1, 18.45),
            ('PR-SJ-1', 'San Juan', 'PR-SJ', -66.1, 18.45),
        ])

        self.assertEqual(where, {'PR-SJ-1': 'PR-SJ'})
        self.assertEqual(aliases, {'US-PR-1': 'PR-SJ-1'})

    def test_two_cities_with_one_name_are_the_same_town_even_when_the_dataset_places_them_far_apart(self):
        # The dataset puts some of them thousands of kilometres from their own island.
        where, aliases = self._run(self.COUNTRIES, self.REGIONS, [
            ('US-PR-1', 'Ponce', 'US-PR', 20.0, 45.0),
            ('PR-PO-1', 'Ponce', 'PR-PO', -66.6, 18.0),
        ])

        self.assertEqual(aliases, {'US-PR-1': 'PR-PO-1'})
        self.assertNotIn('US-PR-1', where)

    def test_any_other_city_moves_to_the_nearest_region_of_the_country(self):
        where, aliases = self._run(self.COUNTRIES, self.REGIONS, [
            ('US-PR-2', 'Bayamón', 'US-PR', -66.17, 18.4),
            ('US-PR-3', 'Yauco', 'US-PR', -66.85, 18.04),
        ])

        self.assertEqual(where, {'US-PR-2': 'PR-SJ', 'US-PR-3': 'PR-PO'})
        self.assertEqual(aliases, {})

    def test_a_city_with_no_position_or_far_from_every_region_stays_where_it_is(self):
        where, _ = self._run(self.COUNTRIES, self.REGIONS, [
            ('US-PR-4', 'Nowhere', 'US-PR', None, None),
            ('US-PR-5', 'Far away', 'US-PR', 10.0, 50.0),
        ])

        self.assertEqual(where, {'US-PR-4': 'US-PR', 'US-PR-5': 'US-PR'})

    def test_ordinary_regions_are_left_alone(self):
        where, aliases = self._run(self.COUNTRIES, self.REGIONS, [
            ('US-AL-1', 'San Juan', 'US-AL', -86.8, 32.8),
            ('US-GA-1', 'Atlanta', 'US-GA', -84.4, 33.7),
            ('PR-SJ-1', 'San Juan', 'PR-SJ', -66.1, 18.45),
        ])

        self.assertEqual(where, {'US-AL-1': 'US-AL', 'US-GA-1': 'US-GA', 'PR-SJ-1': 'PR-SJ'})
        self.assertEqual(aliases, {})

    def test_merging_twice_changes_nothing_more(self):
        cities = [
            ('US-PR-1', 'San Juan', 'US-PR', -66.1, 18.45),
            ('US-PR-2', 'Bayamón', 'US-PR', -66.17, 18.4),
            ('PR-SJ-1', 'San Juan', 'PR-SJ', -66.1, 18.45),
        ]
        with self.command._temp_db() as conn:
            for code, name, lon, lat in self.COUNTRIES:
                conn.execute('INSERT INTO temp_countries (country_code, name, native, longitude, latitude) VALUES (?, ?, ?, ?, ?)', (code, name, '', lon, lat))
            for region_id, name, region_type, code, lon, lat in self.REGIONS:
                conn.execute('INSERT INTO temp_regions (id, name, native, type, country_code, longitude, latitude) VALUES (?, ?, ?, ?, ?, ?, ?)', (region_id, name, '', region_type, code, lon, lat))
            for city_id, name, region_id, lon, lat in cities:
                conn.execute('INSERT INTO temp_cities (id, name, region_id, longitude, latitude) VALUES (?, ?, ?, ?, ?)', (city_id, name, region_id, lon, lat))
            self.command._merge_territory_cities(conn)
            first = conn.execute('SELECT id, region_id FROM temp_cities ORDER BY id').fetchall()
            self.command._merge_territory_cities(conn)
            second = conn.execute('SELECT id, region_id FROM temp_cities ORDER BY id').fetchall()

        self.assertEqual(first, second)


class RemapMergedCitiesTests(TestCase):
    """What happens to a user's visits and places when the duplicate they pointed at is dropped."""

    def setUp(self):
        self.command = Command()
        self.command.stdout = StringIO()
        self.user = CustomUser.objects.create_user(username='remap', email='remap@example.com', password='testpassword123')
        self.other = CustomUser.objects.create_user(username='remap-other', email='remap-other@example.com', password='testpassword123')
        us = Country.objects.create(name='United States', country_code='US')
        pr = Country.objects.create(name='Puerto Rico', country_code='PR')
        us_pr = Region.objects.create(id='US-PR', name='Puerto Rico', country=us, territory=pr)
        san_juan = Region.objects.create(id='PR-SJ', name='San Juan', country=pr)
        self.old = City.objects.create(id='US-PR-1', name='San Juan', region=us_pr)
        self.new = City.objects.create(id='PR-SJ-1', name='San Juan', region=san_juan)

    def _remap(self, aliases):
        with self.command._temp_db() as conn:
            for old_id, new_id in aliases.items():
                conn.execute('INSERT INTO temp_city_aliases (old_id, new_id) VALUES (?, ?)', (old_id, new_id))
            self.command._remap_merged_cities(conn)

    def test_a_visit_to_the_dropped_city_moves_to_the_one_it_was_merged_into(self):
        VisitedCity.objects.create(user=self.user, city=self.old)

        self._remap({'US-PR-1': 'PR-SJ-1'})

        self.assertEqual(list(VisitedCity.objects.filter(user=self.user).values_list('city_id', flat=True)), ['PR-SJ-1'])

    def test_a_user_who_visited_both_keeps_one_visit(self):
        VisitedCity.objects.create(user=self.user, city=self.old)
        VisitedCity.objects.create(user=self.user, city=self.new)
        VisitedCity.objects.create(user=self.other, city=self.old)

        self._remap({'US-PR-1': 'PR-SJ-1'})

        self.assertEqual(list(VisitedCity.objects.filter(user=self.user).values_list('city_id', flat=True)), ['PR-SJ-1'])
        self.assertEqual(list(VisitedCity.objects.filter(user=self.other).values_list('city_id', flat=True)), ['PR-SJ-1'])

    def test_a_place_in_the_dropped_city_is_pointed_at_the_merged_one(self):
        place = Location.objects.create(user=self.user, name='Fort', coordinates=make_point(-66.1, 18.45), city=self.old)

        self._remap({'US-PR-1': 'PR-SJ-1'})

        place.refresh_from_db()
        self.assertEqual(place.city_id, 'PR-SJ-1')

    def test_nothing_is_touched_when_the_target_is_missing(self):
        VisitedCity.objects.create(user=self.user, city=self.old)

        self._remap({'US-PR-1': 'PR-XX-9'})

        self.assertEqual(list(VisitedCity.objects.filter(user=self.user).values_list('city_id', flat=True)), ['US-PR-1'])

    def test_an_empty_alias_table_does_nothing(self):
        VisitedCity.objects.create(user=self.user, city=self.old)

        self._remap({})

        self.assertTrue(VisitedCity.objects.filter(user=self.user, city=self.old).exists())

    def test_the_dropped_id_is_remembered_as_an_alias(self):
        self._remap({'US-PR-1': 'PR-SJ-1'})

        self.assertEqual(CityAlias.objects.get(old_id='US-PR-1').city_id, 'PR-SJ-1')

    def test_remapping_twice_keeps_one_alias(self):
        self._remap({'US-PR-1': 'PR-SJ-1'})
        self._remap({'US-PR-1': 'PR-SJ-1'})

        self.assertEqual(CityAlias.objects.filter(old_id='US-PR-1').count(), 1)

    def test_an_alias_the_data_no_longer_has_is_dropped(self):
        CityAlias.objects.create(old_id='US-PR-7', city=self.new)

        self._remap({'US-PR-1': 'PR-SJ-1'})

        self.assertFalse(CityAlias.objects.filter(old_id='US-PR-7').exists())
        self.assertTrue(CityAlias.objects.filter(old_id='US-PR-1').exists())

    def test_no_alias_is_made_for_a_missing_target(self):
        self._remap({'US-PR-1': 'PR-XX-9'})

        self.assertFalse(CityAlias.objects.exists())


class ResolveCityTests(TestCase):
    def setUp(self):
        pr = Country.objects.create(name='Puerto Rico', country_code='PR')
        region = Region.objects.create(id='PR-SJ', name='San Juan', country=pr)
        self.city = City.objects.create(id='PR-SJ-1', name='San Juan', region=region)
        CityAlias.objects.create(old_id='US-PR-1', city=self.city)

    def test_a_current_id_finds_its_city(self):
        self.assertEqual(resolve_city('PR-SJ-1'), self.city)

    def test_an_id_from_before_the_merge_finds_the_city_it_was_merged_into(self):
        self.assertEqual(resolve_city('US-PR-1'), self.city)

    def test_an_unknown_or_empty_id_finds_nothing(self):
        self.assertIsNone(resolve_city('US-PR-999'))
        self.assertIsNone(resolve_city(''))
        self.assertIsNone(resolve_city(None))
