from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from adventures.services.geocoding.matching import extract_iso_code
from users.models import CustomUser
from worldtravel.models import City, Country, Region


class LocalityMatchTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='geo-user', email='geo-user@example.com', password='testpassword123'
        )
        country = Country.objects.create(name='France', country_code='FR')
        self.region = Region.objects.create(id='FR-IDF', name='Ile-de-France', country=country)
        self.other_region = Region.objects.create(id='FR-ARA', name='Auvergne-Rhone-Alpes', country=country)
        self.paris = City.objects.create(id='FR-IDF-1', name='Paris', region=self.region)
        self.versailles = City.objects.create(id='FR-IDF-2', name='Versailles', region=self.region)
        self.saint_etienne = City.objects.create(id='FR-ARA-1', name='Saint-Étienne', region=self.other_region)
        for index in range(30):
            City.objects.create(id=f'FR-IDF-x{index}', name=f'Filler {index}', region=self.region)

    def data(self, **address):
        return {'name': 'Somewhere', 'address': {'ISO3166-1': 'FR', 'ISO3166-2-lvl4': 'FR-IDF', **address}}

    def test_exact_name_matches(self):
        result = extract_iso_code(self.user, self.data(city='Paris'))

        self.assertEqual(result['city_id'], self.paris.id)
        self.assertEqual(result['region_id'], 'FR-IDF')

    def test_accents_and_punctuation_are_ignored(self):
        result = extract_iso_code(
            self.user,
            {'name': 'x', 'address': {'ISO3166-1': 'FR', 'ISO3166-2-lvl4': 'FR-ARA', 'city': 'saint etienne'}},
        )

        self.assertEqual(result['city_id'], self.saint_etienne.id)

    def test_partial_name_still_matches_as_a_last_resort(self):
        result = extract_iso_code(self.user, self.data(town='Versaill'))

        self.assertEqual(result['city_id'], self.versailles.id)

    def test_the_first_matching_locality_key_wins(self):
        result = extract_iso_code(self.user, self.data(suburb='Nowhere Special', city='Paris', town='Versailles'))

        self.assertEqual(result['city_id'], self.paris.id)

    def test_no_city_match_falls_back_to_the_region(self):
        result = extract_iso_code(self.user, self.data(city='Atlantis'))

        self.assertIsNone(result['city_id'])
        self.assertEqual(result['display_name'], 'Ile-de-France, FR')

    def test_a_regions_cities_are_read_once_however_many_address_keys_miss(self):
        address = {key: 'Atlantis' for key in ('suburb', 'neighbourhood', 'city', 'town', 'village', 'hamlet')}

        with CaptureQueriesContext(connection) as queries:
            extract_iso_code(self.user, self.data(**address))

        city_name_scans = [
            q for q in queries.captured_queries
            if q['sql'].startswith('SELECT "worldtravel_city"."id" AS "id", "worldtravel_city"."name" AS "name" FROM')
        ]
        self.assertEqual(len(city_name_scans), 1)
