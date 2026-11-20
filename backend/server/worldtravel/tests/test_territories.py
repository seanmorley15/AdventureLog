from io import StringIO

from django.test import SimpleTestCase, TestCase

from core.geo import make_point
from worldtravel.management.commands.download_countries import Command
from worldtravel.models import Country, Region
from worldtravel.territories import find_territory_links


def country(code, name, lat, lon, native=None):
    return {'code': code, 'name': name, 'native': native, 'lat': lat, 'lon': lon}


def region(country_code, suffix, name, region_type, lat=None, lon=None, native=None):
    return {
        'id': f'{country_code}-{suffix}', 'country': country_code, 'name': name, 'native': native,
        'type': region_type, 'lat': lat, 'lon': lon,
    }


class FindTerritoryLinksTests(SimpleTestCase):
    def setUp(self):
        self.countries = [
            country('FR', 'France', 46.0, 2.0),
            country('GP', 'Guadeloupe', 16.25, -61.58),
            country('BE', 'Belgium', 50.6, 4.7),
            country('LU', 'Luxembourg', 49.8, 6.1),
            country('GB', 'United Kingdom', 54.0, -2.0),
            country('NF', 'Norfolk Island', -29.03, 167.95),
            country('US', 'United States', 38.0, -97.0),
            country('GE', 'Georgia', 42.0, 43.5),
            country('UM', 'United States Minor Outlying Islands', None, None),
        ]
        self.regions = [
            region('FR', '01', 'Ain', 'metropolitan department', 46.1, 5.3),
            region('FR', '02', 'Aisne', 'metropolitan department', 49.5, 3.6),
            region('FR', '03', 'Allier', 'metropolitan department', 46.4, 3.2),
            region('FR', '971', 'Guadeloupe', 'overseas region', 16.2, -61.5),
            region('BE', 'WAL', 'Wallonia', 'region', 50.4, 4.9),
            region('BE', 'WLX', 'Luxembourg', 'province', 49.9, 5.4),
            region('BE', 'WNA', 'Namur', 'province', 50.3, 4.9),
            region('BE', 'WBR', 'Walloon Brabant', 'province', 50.6, 4.6),
            region('GB', 'ENG', 'England', 'country', 52.0, -1.0),
            region('GB', 'SCT', 'Scotland', 'country', 56.5, -4.2),
            region('GB', 'NFK', 'Norfolk', 'two-tier county', 52.6, 1.3),
            region('GB', 'SFK', 'Suffolk', 'two-tier county', 52.2, 1.0),
            region('GB', 'ESS', 'Essex', 'two-tier county', 51.8, 0.6),
            region('US', 'AL', 'Alabama', 'state', 32.8, -86.8),
            region('US', 'GA', 'Georgia', 'state', 33.0, -83.6),
            region('US', 'AK', 'Alaska', 'state', 64.2, -149.5),
            region('US', 'UM', 'United States Minor Outlying Islands', 'outlying area', 28.2, -177.4),
        ]

    def test_an_overseas_region_is_linked_to_the_country_of_the_same_name(self):
        links = find_territory_links(self.countries, self.regions)

        self.assertEqual(links['FR-971'], 'GP')

    def test_a_region_whose_whole_name_matches_is_linked_even_when_the_country_has_no_position(self):
        links = find_territory_links(self.countries, self.regions)

        self.assertEqual(links['US-UM'], 'UM')

    def test_a_province_named_like_another_country_is_not_linked(self):
        # Luxembourg is an ordinary province of Belgium.
        links = find_territory_links(self.countries, self.regions)

        self.assertNotIn('BE-WLX', links)

    def test_a_state_named_like_another_country_is_not_linked(self):
        links = find_territory_links(self.countries, self.regions)

        self.assertNotIn('US-GA', links)

    def test_a_county_whose_name_only_starts_a_territory_name_is_not_linked(self):
        # "Norfolk" is a county of England, and Norfolk Island is far from England.
        links = find_territory_links(self.countries, self.regions)

        self.assertNotIn('GB-NFK', links)

    def test_a_region_is_linked_by_its_native_name(self):
        countries = [*self.countries, country('RE', 'Reunion', -21.1, 55.5, native='La Réunion')]
        regions = [*self.regions, region('FR', '974', 'Réunion Island', 'overseas region', -21.1, 55.5, native='La Réunion')]

        self.assertEqual(find_territory_links(countries, regions)['FR-974'], 'RE')

    def test_a_region_is_linked_by_a_code_ending_that_is_a_country_code(self):
        # The names differ, but they share words and the region's code is the country's code.
        countries = [*self.countries, country('TF', 'French Southern Territories', -49.25, 69.17)]
        regions = [*self.regions, region('FR', 'TF', 'French Southern and Antarctic Lands', 'overseas territory', -49.25, 69.17)]

        self.assertEqual(find_territory_links(countries, regions)['FR-TF'], 'TF')

    def test_a_code_ending_alone_is_not_enough(self):
        # The region's code is a country's code, but its name shares nothing with that country.
        countries = [*self.countries, country('TF', 'French Southern Territories', -49.25, 69.17)]
        regions = [*self.regions, region('FR', 'TF', 'Tarn-et-Foo', 'overseas territory', 43.0, 1.0)]

        self.assertNotIn('FR-TF', find_territory_links(countries, regions))

    def test_a_country_with_a_single_region_is_never_linked_from(self):
        regions = [region('GP', '00', 'Guadeloupe', '', 16.25, -61.58)]

        self.assertEqual(find_territory_links(self.countries, regions), {})

    def test_two_regions_that_match_two_countries_are_not_linked(self):
        countries = [*self.countries, country('XA', 'Saint Pierre', 1.0, 1.0), country('XB', 'Saint Pierre Island', 1.0, 1.0)]
        regions = [*self.regions, region('FR', 'SP', 'Saint Pierre', 'overseas collectivity', 1.0, 1.0)]

        self.assertNotIn('FR-SP', find_territory_links(countries, regions))


class LinkTerritoriesCommandTests(TestCase):
    """The import step that stores the links, run on rows already read from the dataset."""

    def _link(self, countries, regions):
        command = Command()
        command.stdout = StringIO()
        with command._temp_db() as conn:
            for row in countries:
                conn.execute(
                    'INSERT INTO temp_countries (country_code, name, native, longitude, latitude) VALUES (?, ?, ?, ?, ?)',
                    (row['code'], row['name'], row['native'] or '', row['lon'], row['lat']),
                )
            for row in regions:
                conn.execute(
                    'INSERT INTO temp_regions (id, name, native, type, country_code, longitude, latitude) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (row['id'], row['name'], row['native'] or '', row['type'], row['country'], row['lon'], row['lat']),
                )
            command._link_territories(conn)

    def setUp(self):
        self.france = Country.objects.create(name='France', country_code='FR', coordinates=make_point(2.0, 46.0))
        self.guadeloupe = Country.objects.create(name='Guadeloupe', country_code='GP', coordinates=make_point(-61.58, 16.25))
        for suffix, name in (('01', 'Ain'), ('02', 'Aisne'), ('03', 'Allier')):
            Region.objects.create(id=f'FR-{suffix}', name=name, country=self.france)
        Region.objects.create(id='FR-971', name='Guadeloupe', country=self.france)
        self.countries = [country('FR', 'France', 46.0, 2.0), country('GP', 'Guadeloupe', 16.25, -61.58)]
        self.regions = [
            region('FR', '01', 'Ain', 'metropolitan department', 46.1, 5.3),
            region('FR', '02', 'Aisne', 'metropolitan department', 49.5, 3.6),
            region('FR', '03', 'Allier', 'metropolitan department', 46.4, 3.2),
            region('FR', '971', 'Guadeloupe', 'overseas region', 16.2, -61.5),
        ]

    def test_links_are_stored(self):
        self._link(self.countries, self.regions)

        self.assertEqual(Region.objects.get(id='FR-971').territory, self.guadeloupe)
        self.assertIsNone(Region.objects.get(id='FR-01').territory)

    def test_a_link_the_data_no_longer_supports_is_removed(self):
        Region.objects.filter(id='FR-01').update(territory=self.guadeloupe)

        self._link(self.countries, self.regions)

        self.assertIsNone(Region.objects.get(id='FR-01').territory)
        self.assertEqual(Region.objects.get(id='FR-971').territory, self.guadeloupe)

    def test_linking_twice_changes_nothing(self):
        self._link(self.countries, self.regions)
        self._link(self.countries, self.regions)

        self.assertEqual(Region.objects.filter(territory__isnull=False).count(), 1)
