from django.contrib.gis.geos import Point
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from adventures.models import Location, Transportation
from adventures.serializers import LocationSerializer, MapPinSerializer, TransportationSerializer
from adventures.utils.geo import make_point, point_to_lat_lon, has_coordinates
from users.models import CustomUser


class GeoUtilsTests(TestCase):
    def test_make_point_and_point_to_lat_lon(self):
        point = make_point(-73.968285, 40.785091)
        self.assertIsNotNone(point)
        self.assertEqual(point.srid, 4326)
        lat, lon = point_to_lat_lon(point)
        self.assertAlmostEqual(lat, 40.785091)
        self.assertAlmostEqual(lon, -73.968285)

    def test_make_point_returns_none_for_incomplete_coords(self):
        self.assertIsNone(make_point(None, 40.0))
        self.assertIsNone(make_point(-70.0, None))


class LocationSerializerGeoTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='geo-user',
            email='geo-user@example.com',
            password='testpassword123',
        )
        self.factory = APIRequestFactory()
        self.request = self.factory.post('/')
        self.request.user = self.user

    def _serializer(self):
        return LocationSerializer(context={'request': self.request})

    def test_create_persists_coordinates_from_lat_lon(self):
        serializer = self._serializer()
        location = serializer.create(
            {
                'name': 'Geo Place',
                'latitude': 48.8566,
                'longitude': 2.3522,
                'is_public': False,
            }
        )
        location.refresh_from_db()
        self.assertTrue(has_coordinates(location.coordinates))
        lat, lon = point_to_lat_lon(location.coordinates)
        self.assertAlmostEqual(lat, 48.8566, places=4)
        self.assertAlmostEqual(lon, 2.3522, places=4)

    def test_representation_exposes_lat_lon(self):
        location = Location.objects.create(
            user=self.user,
            name='Stored',
            coordinates=make_point(10.0, 20.0),
        )
        data = self._serializer().to_representation(location)
        self.assertAlmostEqual(data['latitude'], 20.0)
        self.assertAlmostEqual(data['longitude'], 10.0)


class MapPinSerializerGeoTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='pin-user',
            email='pin-user@example.com',
            password='testpassword123',
        )

    def test_map_pin_serializer_lat_lon(self):
        location = Location.objects.create(
            user=self.user,
            name='Pin',
            coordinates=make_point(-122.4, 37.8),
        )
        data = MapPinSerializer(location).data
        self.assertAlmostEqual(data['latitude'], 37.8, places=4)
        self.assertAlmostEqual(data['longitude'], -122.4, places=4)


class TransportationDistanceTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='transport-user',
            email='transport-user@example.com',
            password='testpassword123',
        )
        self.factory = APIRequestFactory()
        self.request = self.factory.get('/')
        self.request.user = self.user

    def test_get_distance_uses_point_fields(self):
        transport = Transportation.objects.create(
            user=self.user,
            type='car',
            name='Trip',
            origin=Point(-74.0, 40.7, srid=4326),
            destination=Point(-118.25, 34.05, srid=4326),
        )
        serializer = TransportationSerializer(
            transport, context={'request': self.request}
        )
        distance = serializer.get_distance(transport)
        self.assertIsNotNone(distance)
        self.assertGreater(distance, 1000)
