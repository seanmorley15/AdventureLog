"""What quick add refuses, and that a refusal leaves nothing behind."""

import uuid
from datetime import date
from unittest.mock import patch

from rest_framework.test import APITestCase

from adventures.models import Collection, Location, Lodging
from adventures.services.day_plan import convert_collection
from core.results import ProviderResult
from core.testing import make_user

LOCATION = '/api/locations/quick-add/'
LODGING = '/api/lodging/quick-add/'


@patch('adventures.services.geocoding.reverse.osm_reverse', return_value=ProviderResult(error='offline'))
class QuickAddErrorTests(APITestCase):
    def setUp(self):
        self.user = make_user('qa-user')
        self.other = make_user('qa-other')
        self.client.force_authenticate(user=self.user)
        self.trip = Collection.objects.create(
            user=self.user, name='Trip', type='trip', start_date=date(2026, 6, 1), end_date=date(2026, 6, 5)
        )
        convert_collection(self.trip)

    def payload(self, **extra):
        return {'name': 'Hut', 'latitude': 67.9, 'longitude': 13.0, **extra}

    def post(self, url, **extra):
        return self.client.post(url, self.payload(**extra), format='json')

    def test_a_missing_name_is_refused(self, _osm):
        for url in (LOCATION, LODGING):
            with self.subTest(url=url):
                response = self.client.post(url, {'latitude': 1, 'longitude': 2}, format='json')
                self.assertEqual((response.status_code, response.json()), (400, {'error': 'name is required'}))

    def test_missing_or_impossible_coordinates_are_refused(self, _osm):
        bad = ({'latitude': None}, {'longitude': 'x'}, {'latitude': 91}, {'longitude': -181})
        for url in (LOCATION, LODGING):
            for extra in bad:
                with self.subTest(url=url, extra=extra):
                    response = self.post(url, **extra)
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.json(), {'error': 'Valid latitude and longitude are required'})

    def test_an_unknown_collection_is_a_404(self, _osm):
        for url in (LOCATION, LODGING):
            with self.subTest(url=url):
                response = self.post(url, collection_id=str(uuid.uuid4()))
                self.assertEqual((response.status_code, response.json()), (404, {'error': 'Collection not found.'}))

    def test_a_collection_id_that_is_not_an_id_is_a_404_not_a_server_error(self, _osm):
        for url in (LOCATION, LODGING):
            with self.subTest(url=url):
                response = self.post(url, collection_id='not-a-uuid')
                self.assertEqual((response.status_code, response.json()), (404, {'error': 'Collection not found.'}))

    def test_a_collection_the_user_cannot_edit_is_a_403_naming_what_was_being_added(self, _osm):
        theirs = Collection.objects.create(user=self.other, name='Theirs')
        expected = {
            LOCATION: 'You do not have permission to add this location to the selected collection.',
            LODGING: 'You do not have permission to add this lodging to the selected collection.',
        }
        for url, message in expected.items():
            with self.subTest(url=url):
                response = self.post(url, collection_id=str(theirs.id))
                self.assertEqual((response.status_code, response.json()), (403, {'error': message}))
        self.assertFalse(Location.objects.filter(collections=theirs).exists())

    def test_a_category_must_be_an_object_or_a_string(self, _osm):
        response = self.post(LOCATION, category=123)
        self.assertEqual((response.status_code, response.json()), (400, {'error': 'category must be an object or string'}))

    def test_an_id_for_a_category_that_is_not_the_users_is_refused(self, _osm):
        response = self.post(LOCATION, category=str(uuid.uuid4()))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'error': 'Category not found or inaccessible'})

    def test_a_date_before_or_after_the_trip_is_refused_with_its_own_message(self, _osm):
        cases = (('2026-05-31', 'before the collection start_date'), ('2026-06-06', 'after the collection end_date'))
        for url in (LOCATION, LODGING):
            for day, wording in cases:
                with self.subTest(url=url, day=day):
                    response = self.post(url, collection_id=str(self.trip.id), itinerary_date=day)
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(wording, response.json()['error'])

    def test_a_refused_date_leaves_nothing_behind(self, _osm):
        self.post(LOCATION, name='Ghost place', collection_id=str(self.trip.id), itinerary_date='2027-01-01')
        self.post(LODGING, name='Ghost lodge', collection_id=str(self.trip.id), itinerary_date='2027-01-01')

        self.assertFalse(Location.objects.filter(name='Ghost place').exists())
        self.assertFalse(Lodging.objects.filter(name='Ghost lodge').exists())
        self.assertFalse(self.trip.itinerary_items.exists())

    def test_a_date_inside_the_trip_places_the_new_record_on_that_day(self, _osm):
        response = self.post(LOCATION, collection_id=str(self.trip.id), itinerary_date='2026-06-03')

        self.assertEqual(response.status_code, 201, response.content)
        placement = self.trip.itinerary_items.get()
        self.assertEqual(str(placement.object_id), response.json()['id'])
        self.assertEqual(placement.day.index, 3)
