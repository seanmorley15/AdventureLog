import io
import json
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from adventures.models import Location
from adventures.utils.collection_type import BACKUP_SCHEMA
from core.geo import make_point
from users.models import CustomUser
from worldtravel.models import City, CityAlias, Country, Region, VisitedCity


class RestoreTerritoryTests(APITestCase):
    """A backup made before Puerto Rico's cities were merged onto the country still finds them."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='restore-user', email='restore-user@example.com', password='testpassword123'
        )
        self.client.force_authenticate(user=self.user)

        self.us = Country.objects.create(name='United States', country_code='US', coordinates=make_point(-97.0, 38.0))
        self.pr = Country.objects.create(name='Puerto Rico', country_code='PR', coordinates=make_point(-66.5, 18.25))
        self.alabama = Region.objects.create(id='US-AL', name='Alabama', country=self.us, coordinates=make_point(-86.8, 32.8))
        self.us_pr = Region.objects.create(id='US-PR', name='Puerto Rico', country=self.us, territory=self.pr, coordinates=make_point(-66.5, 18.25))
        self.san_juan = Region.objects.create(id='PR-SJ', name='San Juan', country=self.pr, coordinates=make_point(-66.1, 18.45))
        self.ponce = Region.objects.create(id='PR-PO', name='Ponce', country=self.pr, coordinates=make_point(-66.6, 18.0))
        self.city = City.objects.create(id='PR-SJ-1', name='San Juan', region=self.san_juan, coordinates=make_point(-66.1, 18.45))
        self.mobile = City.objects.create(id='US-AL-1', name='Mobile', region=self.alabama)
        # The duplicate the world data import dropped, and a city it moved (the id is unchanged).
        CityAlias.objects.create(old_id='US-PR-1', city=self.city)
        self.moved = City.objects.create(id='US-PR-3', name='Bayamón', region=self.san_juan, coordinates=make_point(-66.17, 18.4))

    def _restore(self, **backup):
        payload = {'backup_schema': BACKUP_SCHEMA, 'collections': [], 'locations': [], **backup}
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('data.json', json.dumps(payload))
        upload = SimpleUploadedFile('backup.zip', buffer.getvalue(), content_type='application/zip')
        response = self.client.post('/api/backup/import/', {'file': upload, 'confirm': 'yes'}, format='multipart')
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()['summary']

    def _place(self, **fields):
        return {'export_id': 'loc_0', 'name': 'Castillo', 'latitude': 18.46, 'longitude': -66.12, 'country_code': 'US', **fields}

    def test_a_visit_to_a_dropped_city_is_restored_on_the_city_it_was_merged_into(self):
        summary = self._restore(visited_cities=[{'city': 'US-PR-1'}])

        self.assertEqual(summary['visited_cities'], 1)
        self.assertEqual(list(VisitedCity.objects.filter(user=self.user).values_list('city_id', flat=True)), ['PR-SJ-1'])

    def test_a_visit_to_a_city_that_was_moved_keeps_its_id(self):
        self._restore(visited_cities=[{'city': 'US-PR-3'}])

        self.assertEqual(list(VisitedCity.objects.filter(user=self.user).values_list('city_id', flat=True)), ['US-PR-3'])

    def test_a_visit_to_a_city_that_never_existed_is_skipped(self):
        summary = self._restore(visited_cities=[{'city': 'US-PR-999'}])

        self.assertEqual(summary['visited_cities'], 0)

    def test_a_place_in_a_dropped_city_lands_on_the_territory(self):
        self._restore(locations=[self._place(city='US-PR-1', region='US-PR')])

        place = Location.objects.get(user=self.user, name='Castillo')
        self.assertEqual(place.city_id, 'PR-SJ-1')
        self.assertEqual(place.region_id, 'PR-SJ')
        self.assertEqual(place.country.country_code, 'PR')

    def test_a_place_in_the_region_under_the_larger_country_lands_in_the_territorys_nearest_region(self):
        self._restore(locations=[self._place(region='US-PR', latitude=18.0, longitude=-66.6)])

        place = Location.objects.get(user=self.user, name='Castillo')
        self.assertEqual(place.region_id, 'PR-PO')
        self.assertEqual(place.country.country_code, 'PR')
        self.assertIsNone(place.city_id)

    def test_a_place_with_no_position_gets_the_territory_but_no_region(self):
        self._restore(locations=[self._place(region='US-PR', latitude=None, longitude=None)])

        place = Location.objects.get(user=self.user, name='Castillo')
        self.assertIsNone(place.region_id)
        self.assertEqual(place.country.country_code, 'PR')

    def test_an_ordinary_place_is_restored_as_before(self):
        self._restore(locations=[self._place(city='US-AL-1', region='US-AL', latitude=30.69, longitude=-88.04)])

        place = Location.objects.get(user=self.user, name='Castillo')
        self.assertEqual((place.city_id, place.region_id, place.country.country_code), ('US-AL-1', 'US-AL', 'US'))

    def test_a_place_with_a_city_that_never_existed_still_restores(self):
        self._restore(locations=[self._place(city='US-PR-999', region='US-PR')])

        place = Location.objects.get(user=self.user, name='Castillo')
        self.assertIsNone(place.city_id)
        self.assertEqual(place.country.country_code, 'PR')
