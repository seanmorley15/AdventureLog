from datetime import timedelta
from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase, override_settings
from django.utils import timezone

from adventures.models import Location, Visit
from core.results import ProviderResult
from adventures.services.geocoding.reverse import reverse_geocode
from core.geo import make_point
from users.models import CustomUser
from worldtravel.models import City, Country, Region, VisitedCity, VisitedRegion

GOOGLE_RESULTS = {
    'results': [
        {
            'formatted_address': '75001 Paris, France',
            'types': ['point_of_interest', 'establishment'],
            'address_components': [
                {'long_name': 'Musee du Louvre', 'short_name': 'Louvre', 'types': ['point_of_interest']},
                {'long_name': 'Paris', 'short_name': 'Paris', 'types': ['locality']},
                {'long_name': 'Ile-de-France', 'short_name': 'IDF', 'types': ['administrative_area_level_1']},
                {'long_name': 'France', 'short_name': 'FR', 'types': ['country']},
            ],
        }
    ]
}

OSM_DATA = {
    'name': 'Eiffel Tower',
    'display_name': 'Eiffel Tower, Paris, France',
    'address': {'ISO3166-1': 'FR', 'ISO3166-2-lvl4': 'FR-IDF', 'city': 'Paris'},
}


def _nearby_response(*names):
    response = MagicMock()
    response.json.return_value = {'places': [{'displayName': {'text': name}} for name in names]}
    return response


class GeocodeFixtureMixin:
    def build_geography(self):
        self.user = CustomUser.objects.create_user(
            username='rg-user', email='rg-user@example.com', password='testpassword123'
        )
        self.country = Country.objects.create(name='France', country_code='FR', coordinates=make_point(2.2, 46.2))
        self.region = Region.objects.create(id='FR-IDF', name='Ile-de-France', country=self.country)
        self.city = City.objects.create(id='FR-IDF-1', name='Paris', region=self.region)


class ReverseGeocodeProviderFlowTests(GeocodeFixtureMixin, TestCase):
    def setUp(self):
        self.build_geography()

    @override_settings(GOOGLE_MAPS_API_KEY='key')
    def test_google_result_is_matched_and_prefers_the_nearby_place_name(self):
        with patch('adventures.services.geocoding.reverse.google_reverse',
                   return_value=ProviderResult(data=GOOGLE_RESULTS)), \
                patch('requests.post', return_value=_nearby_response('Pyramide du Louvre')) as post:
            result = reverse_geocode(48.86, 2.33, self.user)

        self.assertEqual(result.provider_used, 'google')
        self.assertEqual(result.data['location_name'], 'Pyramide du Louvre')
        self.assertEqual(result.data['region_id'], 'FR-IDF')
        self.assertEqual(result.data['city_id'], 'FR-IDF-1')
        self.assertEqual(result.data['provider'], 'google')
        sent = post.call_args.kwargs
        self.assertEqual(sent['headers']['X-Goog-Api-Key'], 'key')
        self.assertEqual(sent['json']['locationRestriction']['circle']['center'], {'latitude': 48.86, 'longitude': 2.33})

    @override_settings(GOOGLE_MAPS_API_KEY='key')
    def test_failed_nearby_lookup_falls_back_to_the_address_component_name(self):
        with patch('adventures.services.geocoding.reverse.google_reverse',
                   return_value=ProviderResult(data=GOOGLE_RESULTS)), \
                patch('requests.post', side_effect=requests.exceptions.ConnectionError):
            result = reverse_geocode(48.86, 2.33, self.user)

        self.assertEqual(result.provider_used, 'google')
        self.assertEqual(result.data['location_name'], 'Musee du Louvre')

    @override_settings(GOOGLE_MAPS_API_KEY='key')
    def test_street_address_nearby_names_are_not_used(self):
        with patch('adventures.services.geocoding.reverse.google_reverse',
                   return_value=ProviderResult(data=GOOGLE_RESULTS)), \
                patch('requests.post', return_value=_nearby_response('12 Main Street, Paris')):
            result = reverse_geocode(48.86, 2.33, self.user)

        self.assertEqual(result.data['location_name'], 'Musee du Louvre')

    @override_settings(GOOGLE_MAPS_API_KEY=None)
    def test_without_a_google_key_osm_is_used_and_google_is_never_called(self):
        with patch('adventures.services.geocoding.reverse.google_reverse') as google, \
                patch('requests.post') as post, \
                patch('adventures.services.geocoding.reverse.osm_reverse',
                      return_value=ProviderResult(data=dict(OSM_DATA))):
            result = reverse_geocode(48.85, 2.29, self.user)

        google.assert_not_called()
        post.assert_not_called()
        self.assertEqual(result.provider_used, 'osm')
        self.assertEqual(result.data['location_name'], 'Eiffel Tower')
        self.assertEqual(result.data['city_id'], 'FR-IDF-1')

    @override_settings(GOOGLE_MAPS_API_KEY='key')
    def test_a_google_error_falls_back_to_osm(self):
        with patch('adventures.services.geocoding.reverse.google_reverse',
                   return_value=ProviderResult(error='Google Maps service error')), \
                patch('adventures.services.geocoding.reverse.osm_reverse',
                      return_value=ProviderResult(data=dict(OSM_DATA))):
            result = reverse_geocode(48.85, 2.29, self.user)

        self.assertEqual(result.provider_used, 'osm')

    @override_settings(GOOGLE_MAPS_API_KEY=None)
    def test_when_both_fail_the_result_is_an_error(self):
        with patch('adventures.services.geocoding.reverse.osm_reverse',
                   return_value=ProviderResult(error='OpenStreetMap service error')):
            result = reverse_geocode(48.85, 2.29, self.user)

        self.assertIsNone(result.provider_used)
        self.assertEqual(result.data, {'error': 'Unable to reverse geocode location.'})


@override_settings(GOOGLE_MAPS_API_KEY=None)
class BackgroundGeocodeAssignTests(GeocodeFixtureMixin, TestCase):
    def setUp(self):
        self.build_geography()

    def _location(self, name, visited):
        location = Location.objects.create(user=self.user, name=name, coordinates=make_point(2.29, 48.85))
        if visited:
            now = timezone.now()
            Visit.objects.create(location=location, start_date=now - timedelta(days=3), end_date=now - timedelta(days=2))
        return location

    def _run(self, location):
        from adventures.services.geocoding.assignment import geocode_and_assign_location

        with patch('adventures.services.geocoding.reverse.osm_reverse',
                   return_value=ProviderResult(data=dict(OSM_DATA))):
            geocode_and_assign_location(str(location.id))
        location.refresh_from_db()

    def test_assigns_country_region_and_city_and_marks_a_visited_place(self):
        location = self._location('Tower', visited=True)

        self._run(location)

        self.assertEqual((location.country_id, location.region_id, location.city_id),
                         (self.country.pk, 'FR-IDF', 'FR-IDF-1'))
        self.assertTrue(VisitedRegion.objects.filter(user=self.user, region=self.region).exists())
        self.assertTrue(VisitedCity.objects.filter(user=self.user, city=self.city).exists())

    def test_a_place_that_was_not_visited_is_assigned_but_not_marked(self):
        location = self._location('Wishlist', visited=False)

        self._run(location)

        self.assertEqual(location.region_id, 'FR-IDF')
        self.assertFalse(VisitedRegion.objects.exists())
        self.assertFalse(VisitedCity.objects.exists())

    def test_a_place_without_coordinates_is_left_alone(self):
        location = Location.objects.create(user=self.user, name='Nowhere')

        with patch('adventures.services.geocoding.reverse.osm_reverse') as osm:
            from adventures.services.geocoding.assignment import geocode_and_assign_location
            geocode_and_assign_location(str(location.id))

        osm.assert_not_called()

    def test_a_geocoding_failure_is_swallowed(self):
        location = self._location('Broken', visited=True)

        with patch('adventures.services.geocoding.reverse.osm_reverse', side_effect=RuntimeError('boom')):
            from adventures.services.geocoding.assignment import geocode_and_assign_location
            geocode_and_assign_location(str(location.id))

        location.refresh_from_db()
        self.assertIsNone(location.region_id)
