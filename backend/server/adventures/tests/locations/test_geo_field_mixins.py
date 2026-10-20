from rest_framework import serializers
from rest_framework.test import APITestCase

from adventures.models import Location, Transportation
from adventures.serializers import ActivitySerializer, LocationSerializer, TransportationSerializer
from core.geo import point_to_lat_lon
from users.models import CustomUser

LAT_LON_MESSAGE = 'Valid latitude and longitude are required together.'


class GeoFieldMixinTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='geo-mixin-user', email='geo-mixin-user@example.com', password='testpassword123'
        )
        self.client.force_authenticate(user=self.user)

    def test_declared_fields_exist_in_the_expected_order(self):
        self.assertIn('latitude', LocationSerializer().fields)
        self.assertIn('longitude', LocationSerializer().fields)
        transport = TransportationSerializer().fields
        for name in ('origin_latitude', 'origin_longitude', 'destination_latitude', 'destination_longitude'):
            self.assertIn(name, transport)
        activity = ActivitySerializer().fields
        for name in ('start_lat', 'start_lng', 'end_lat', 'end_lng'):
            self.assertIn(name, activity)

    def test_pair_becomes_a_point_and_is_read_back(self):
        response = self.client.post('/api/locations/', {'name': 'Reine', 'latitude': 67.9, 'longitude': 13.0}, format='json')

        self.assertEqual(response.status_code, 201, response.content)
        place = Location.objects.get(id=response.json()['id'])
        self.assertEqual(point_to_lat_lon(place.coordinates), (67.9, 13.0))
        self.assertEqual((response.json()['latitude'], response.json()['longitude']), (67.9, 13.0))

    def test_both_null_clears_the_point(self):
        place = Location.objects.create(user=self.user, name='Reine')
        self.client.patch(f'/api/locations/{place.id}/', {'latitude': 67.9, 'longitude': 13.0}, format='json')

        response = self.client.patch(f'/api/locations/{place.id}/', {'latitude': None, 'longitude': None}, format='json')

        self.assertEqual(response.status_code, 200, response.content)
        place.refresh_from_db()
        self.assertIsNone(place.coordinates)

    def test_leaving_both_out_keeps_the_point(self):
        place = Location.objects.create(user=self.user, name='Reine')
        self.client.patch(f'/api/locations/{place.id}/', {'latitude': 67.9, 'longitude': 13.0}, format='json')

        self.client.patch(f'/api/locations/{place.id}/', {'name': 'Renamed'}, format='json')

        place.refresh_from_db()
        self.assertEqual(point_to_lat_lon(place.coordinates), (67.9, 13.0))

    def test_one_of_the_pair_is_refused_with_a_plain_message(self):
        response = self.client.post('/api/locations/', {'name': 'Reine', 'latitude': 67.9}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), [LAT_LON_MESSAGE])

    def test_transport_endpoints_report_the_error_against_the_latitude_field(self):
        response = self.client.post(
            '/api/transportations/',
            {'name': 'Train', 'type': 'train', 'origin_latitude': 48.8},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'origin_latitude': LAT_LON_MESSAGE})

        response = self.client.post(
            '/api/transportations/',
            {'name': 'Train', 'type': 'train', 'destination_longitude': 4.8},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'destination_latitude': LAT_LON_MESSAGE})

    def test_transport_pairs_become_points(self):
        response = self.client.post(
            '/api/transportations/',
            {
                'name': 'Train', 'type': 'train',
                'origin_latitude': 48.85, 'origin_longitude': 2.35,
                'destination_latitude': 45.76, 'destination_longitude': 4.83,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.content)
        trip = Transportation.objects.get(id=response.json()['id'])
        self.assertEqual(point_to_lat_lon(trip.origin), (48.85, 2.35))
        self.assertEqual(point_to_lat_lon(trip.destination), (45.76, 4.83))

    def test_activity_points_use_start_and_end_names(self):
        mixin = ActivitySerializer()

        data = mixin._pop_activity_points({'start_lat': 1.0, 'start_lng': 2.0, 'end_lat': None, 'end_lng': None, 'name': 'x'})

        self.assertEqual(point_to_lat_lon(data['start_point']), (1.0, 2.0))
        self.assertIsNone(data['end_point'])
        self.assertEqual(data['name'], 'x')
        self.assertNotIn('start_lat', data)

    def test_activity_half_a_pair_is_refused_against_the_latitude_field(self):
        with self.assertRaises(serializers.ValidationError) as caught:
            ActivitySerializer()._pop_activity_points({'end_lng': 2.0})

        self.assertEqual(
            {key: str(value) for key, value in caught.exception.detail.items()},
            {'end_lat': 'Valid start/end coordinates are required together.'},
        )
