from django.test import TestCase

from adventures.utils.geocoding_utils import extractIsoCode
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
        aland = Country.objects.create(name='Aland Islands', country_code='AX')
        Region.objects.create(id='AX-00', name='Aland Islands', country=aland)
        curacao = Country.objects.create(name='Curaçao', country_code='CW')
        Region.objects.create(id='CW-00', name='Curaçao', country=curacao)
        united_states = Country.objects.create(name='United States', country_code='US')
        puerto_rico = Region.objects.create(id='US-PR', name='Puerto Rico', country=united_states)
        City.objects.create(id='US-PR-1', name='San Juan', region=puerto_rico)
        pr = Country.objects.create(name='Puerto Rico', country_code='PR')
        Region.objects.create(id='PR-00', name='Puerto Rico', country=pr)

    def _aland_address(self, town):
        # Nominatim reverse result for Mariehamn (60.102423, 19.941260), see #1212
        return {
            'address': {
                'town': town,
                'county': 'Åland',
                'ISO3166-2-lvl3': 'FI-01',
                'state': 'Åland',
                'ISO3166-2-lvl4': 'FI-01',
                'country': 'Suomi / Finland',
                'country_code': 'fi',
            }
        }

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

        result = extractIsoCode(self.user, data)

        self.assertEqual(result['region_id'], 'GI-00')
        self.assertEqual(result['country_id'], 'GI')

    def test_unknown_country_still_reports_no_region(self):
        data = {'address': {'country': 'Nowhere', 'country_code': 'zz'}}

        self.assertEqual(extractIsoCode(self.user, data), {'error': 'No region found'})

    def test_aland_finnish_subdivision_code_matches_aland_country(self):
        result = extractIsoCode(self.user, self._aland_address('Mariehamn'))

        self.assertEqual(result['region_id'], 'AX-00')
        self.assertEqual(result['country_id'], 'AX')

    def test_aland_matches_with_finnish_language_response(self):
        result = extractIsoCode(self.user, self._aland_address('Maarianhamina'))

        self.assertEqual(result['region_id'], 'AX-00')
        self.assertEqual(result['country_id'], 'AX')

    def test_curacao_dutch_subdivision_code_matches_curacao_country(self):
        data = {
            'address': {
                'city': 'Willemstad',
                'ISO3166-2-lvl3': 'NL-CW',
                'country': 'Curaçao',
                'country_code': 'nl',
            }
        }

        result = extractIsoCode(self.user, data)

        self.assertEqual(result['region_id'], 'CW-00')
        self.assertEqual(result['country_id'], 'CW')

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

        result = extractIsoCode(self.user, data)

        self.assertEqual(result['region_id'], 'US-PR')
        self.assertEqual(result['country_id'], 'US')
        self.assertEqual(result['city_id'], 'US-PR-1')
