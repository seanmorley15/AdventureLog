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
        aland = Country.objects.create(name='Aland Islands', country_code='AX')
        Region.objects.create(id='AX-02', name='Jomala', country=aland)
        mariehamn = Region.objects.create(id='AX-01', name='Mariehamn', country=aland)
        City.objects.create(id='AX-01-1', name='Mariehamn', region=mariehamn)

    def test_aland_finnish_subdivision_code_matches_aland_country(self):
        """OSM tags Åland as FI-01 while the travel database stores it as country AX (#1212)."""
        data = {
            'address': {
                'suburb': 'Vreten',
                'city_district': 'Vreten',
                'town': 'Mariehamn',
                'municipality': 'Mariehamns stad',
                'county': 'Åland',
                'ISO3166-2-lvl3': 'FI-01',
                'state': 'Åland',
                'ISO3166-2-lvl4': 'FI-01',
                'country': 'Suomi / Finland',
                'country_code': 'fi',
            }
        }

        result = extractIsoCode(self.user, data)

        self.assertEqual(result.get('country_id'), 'AX')
        self.assertEqual(result.get('region_id'), 'AX-01')
        self.assertEqual(result.get('city'), 'Mariehamn')
        self.assertEqual(result.get('city_id'), 'AX-01-1')
