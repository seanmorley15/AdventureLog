from django.test import TestCase

from adventures.utils.geocoding_utils import extractIsoCode
from users.models import CustomUser
from worldtravel.models import Country, Region


class ExtractIsoCodeTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='geocode-user',
            email='geocode-user@example.com',
            password='testpassword123',
        )
        self.gibraltar = Country.objects.create(name='Gibraltar', country_code='GI')
        Region.objects.create(id='GI-00', name='Gibraltar', country=self.gibraltar)

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
