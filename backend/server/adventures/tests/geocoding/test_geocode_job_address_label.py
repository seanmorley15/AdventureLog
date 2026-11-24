from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from adventures.models import Location
from adventures.services.geocoding.assignment import geocode_and_assign_location
from core.geo import make_point
from users.models import CustomUser
from worldtravel.models import Country

RESULT = {'display_name': 'Petersburg, West Virginia, US', 'country_id': 'US'}


class GeocodeJobAddressLabelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='lbl', email='lbl@example.com', password='testpassword123')
        Country.objects.create(name='United States', country_code='US', coordinates=make_point(-98, 39))

    def _run(self, **fields):
        loc = Location.objects.create(user=self.user, name='Seneca Rocks', coordinates=make_point(-79.37, 38.83), **fields)
        with patch(
            'adventures.services.geocoding.assignment.reverse_geocode_service',
            return_value=SimpleNamespace(data=RESULT),
        ):
            geocode_and_assign_location(str(loc.id))
        loc.refresh_from_db()
        return loc

    def test_a_place_without_an_address_gets_the_city_region_country_label(self):
        self.assertEqual(self._run().location, 'Petersburg, West Virginia, US')

    def test_an_address_someone_typed_is_kept(self):
        self.assertEqual(self._run(location='My cabin').location, 'My cabin')
