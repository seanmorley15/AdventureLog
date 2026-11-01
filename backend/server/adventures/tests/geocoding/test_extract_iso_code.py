from django.test import TestCase

from adventures.services.geocoding.matching import extract_iso_code
from users.models import CustomUser
from worldtravel.models import City, Country, Region


class ExtractIsoCodeTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='geocode-user',
            email='geocode-user@example.com',
            password='testpassword123',
        )
        self.gibraltar = Country.objects.create(name='Gibraltar', country_code='GI')
        Region.objects.create(id='GI-00', name='Gibraltar', country=self.gibraltar)
        # dr5hn v3.2 municipalities for AX. Mariehamn's imported city id is AX-01-160425.
        aland = Country.objects.create(name='Aland Islands', country_code='AX')
        aland_municipalities = (
            ('01', 'Mariehamn'),
            ('02', 'Jomala'),
            ('03', 'Finström'),
            ('04', 'Lemland'),
            ('05', 'Saltvik'),
            ('06', 'Hammarland'),
            ('07', 'Sund'),
            ('08', 'Eckerö'),
            ('09', 'Föglö'),
            ('10', 'Geta'),
            ('11', 'Vårdö'),
            ('12', 'Brändö'),
            ('13', 'Lumparland'),
            ('14', 'Kumlinge'),
            ('15', 'Kökar'),
            ('16', 'Sottunga'),
        )
        mariehamn = None
        for iso2, name in aland_municipalities:
            region = Region.objects.create(id=f'AX-{iso2}', name=name, country=aland)
            if iso2 == '01':
                mariehamn = region
        City.objects.create(id='AX-01-160425', name='Mariehamn', region=mariehamn)
        curacao = Country.objects.create(name='Curaçao', country_code='CW')
        Region.objects.create(id='CW-00', name='Curaçao', country=curacao)
        sint_maarten = Country.objects.create(name='Sint Maarten (Dutch part)', country_code='SX')
        Region.objects.create(id='SX-00', name='Sint Maarten (Dutch part)', country=sint_maarten)
        united_states = Country.objects.create(name='United States', country_code='US')
        puerto_rico = Region.objects.create(id='US-PR', name='Puerto Rico', country=united_states)
        City.objects.create(id='US-PR-1', name='San Juan', region=puerto_rico)
        pr = Country.objects.create(name='Puerto Rico', country_code='PR')
        Region.objects.create(id='PR-00', name='Puerto Rico', country=pr)

    def _assert_mariehamn(self, result):
        self.assertEqual(result['region_id'], 'AX-01')
        self.assertEqual(result['region'], 'Mariehamn')
        self.assertEqual(result['country_id'], 'AX')
        self.assertEqual(result['city'], 'Mariehamn')
        self.assertEqual(result['city_id'], 'AX-01-160425')

    def test_country_without_subdivisions_uses_its_single_region(self):
        # Nominatim reverse result for 36.128593, -5.347476: no ISO3166 keys at all
        data = {
            'address': {
                'road': 'Royal Anglian Way',
                'city': 'Gibraltar',
                'country': 'Gibraltar',
                'country_code': 'gi',
            }
        }

        result = extract_iso_code(self.user, data)

        self.assertEqual(result['region_id'], 'GI-00')
        self.assertEqual(result['country_id'], 'GI')

    def test_unknown_country_still_reports_no_region(self):
        data = {'address': {'country': 'Nowhere', 'country_code': 'zz'}}

        self.assertEqual(extract_iso_code(self.user, data), {'error': 'No region found'})

    def test_aland_finnish_subdivision_code_matches_mariehamn(self):
        # Nominatim reverse (zoom 18) for Mariehamn (60.102423, 19.941260), see #1212.
        # "Mariehamn sub-region" is the sub-region; the municipality itself is the town.
        data = {
            'address': {
                'suburb': 'Vreten',
                'city_district': 'Vreten',
                'town': 'Mariehamn',
                'municipality': 'Mariehamn sub-region',
                'county': 'Åland Islands',
                'ISO3166-2-lvl3': 'FI-01',
                'state': 'Åland Islands',
                'ISO3166-2-lvl4': 'FI-01',
                'country': 'Finland',
                'country_code': 'fi',
            }
        }

        self._assert_mariehamn(extract_iso_code(self.user, data))

    def test_aland_matches_with_finnish_language_response(self):
        # Same point with Accept-Language: fi. Town and municipality use the Finnish spelling.
        data = {
            'address': {
                'suburb': 'Vreten',
                'city_district': 'Vreten',
                'town': 'Maarianhamina',
                'municipality': 'Maarianhaminan kaupunki',
                'county': 'Ahvenanmaa',
                'ISO3166-2-lvl3': 'FI-01',
                'state': 'Ahvenanmaa',
                'ISO3166-2-lvl4': 'FI-01',
                'country': 'Suomi',
                'country_code': 'fi',
            }
        }

        self._assert_mariehamn(extract_iso_code(self.user, data))

    def test_aland_town_selects_municipality_inside_a_shared_subregion(self):
        # Jomala's municipality field is the countryside sub-region, not Jomala itself.
        data = {
            'address': {
                'town': 'Jomala',
                'municipality': 'Ålands Countryside',
                'county': 'Åland Islands',
                'ISO3166-2-lvl3': 'FI-01',
                'state': 'Åland Islands',
                'ISO3166-2-lvl4': 'FI-01',
                'country': 'Finland',
                'country_code': 'fi',
            }
        }

        result = extract_iso_code(self.user, data)

        self.assertEqual(result['region_id'], 'AX-02')
        self.assertEqual(result['region'], 'Jomala')
        self.assertEqual(result['country_id'], 'AX')
        self.assertIsNone(result['city'])

    def test_aland_municipality_field_matches_when_town_is_absent(self):
        # Smaller municipalities come back as the municipality boundary, with no town.
        data = {
            'address': {
                'municipality': 'Finström',
                'ISO3166-2-lvl4': 'FI-01',
                'state': 'Åland Islands',
                'country': 'Finland',
                'country_code': 'fi',
            }
        }

        result = extract_iso_code(self.user, data)

        self.assertEqual(result['region_id'], 'AX-03')
        self.assertEqual(result['region'], 'Finström')
        self.assertEqual(result['country_id'], 'AX')
        self.assertIsNone(result['city'])

    def test_curacao_dutch_subdivision_code_matches_curacao_country(self):
        data = {
            'address': {
                'city': 'Willemstad',
                'ISO3166-2-lvl3': 'NL-CW',
                'country': 'Curaçao',
                'country_code': 'nl',
            }
        }

        result = extract_iso_code(self.user, data)

        self.assertEqual(result['region_id'], 'CW-00')
        self.assertEqual(result['country_id'], 'CW')

    def test_sint_maarten_dutch_subdivision_code_matches_sint_maarten_country(self):
        # Nominatim search for Philipsburg: town and municipality, subdivision NL-SX.
        data = {
            'address': {
                'town': 'Philipsburg',
                'municipality': 'Philipsburg',
                'country': 'Sint Maarten',
                'ISO3166-2-lvl3': 'NL-SX',
                'country_code': 'nl',
            }
        }

        result = extract_iso_code(self.user, data)

        self.assertEqual(result['region_id'], 'SX-00')
        self.assertEqual(result['country_id'], 'SX')

    def test_puerto_rico_stays_with_united_states(self):
        data = {
            'address': {
                'city': 'San Juan',
                'state': 'Puerto Rico',
                'ISO3166-2-lvl4': 'US-PR',
                'country': 'United States',
                'country_code': 'us',
            }
        }

        result = extract_iso_code(self.user, data)

        self.assertEqual(result['region_id'], 'US-PR')
        self.assertEqual(result['country_id'], 'US')
        self.assertEqual(result['city_id'], 'US-PR-1')
