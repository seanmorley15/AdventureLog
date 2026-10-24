from django.contrib.gis.geos import Point
from django.test import TestCase

from adventures.utils.geo import make_point
from worldtravel.models import City, Country, Region
from worldtravel.serializers import CitySerializer, CountrySerializer, RegionSerializer


class WorldtravelLatLonSerializerTests(TestCase):
    def setUp(self):
        self.country = Country.objects.create(
            name='United States',
            country_code='US',
            coordinates=make_point(-95.712891, 37.09024),
        )
        self.region = Region.objects.create(
            id='US-AL',
            name='Alabama',
            country=self.country,
            coordinates=make_point(-86.902298, 32.318231),
        )
        self.city = City.objects.create(
            id='US-AL-110968',
            name='Abbeville',
            region=self.region,
            coordinates=make_point(-85.250488, 31.571836),
        )

    def test_city_serializer_includes_lat_lon(self):
        data = CitySerializer(self.city).data
        self.assertIn('latitude', data)
        self.assertIn('longitude', data)
        self.assertAlmostEqual(data['latitude'], 31.571836, places=4)
        self.assertAlmostEqual(data['longitude'], -85.250488, places=4)

    def test_region_serializer_includes_lat_lon(self):
        data = RegionSerializer(self.region).data
        self.assertIn('latitude', data)
        self.assertIn('longitude', data)
        self.assertAlmostEqual(data['latitude'], 32.318231, places=4)
        self.assertAlmostEqual(data['longitude'], -86.902298, places=4)

    def test_country_serializer_includes_lat_lon(self):
        data = CountrySerializer(self.country).data
        self.assertIn('latitude', data)
        self.assertIn('longitude', data)
        self.assertAlmostEqual(data['latitude'], 37.09024, places=4)
        self.assertAlmostEqual(data['longitude'], -95.712891, places=4)

    def test_city_serializer_null_coordinates(self):
        self.city.coordinates = None
        self.city.save(update_fields=['coordinates'])
        data = CitySerializer(self.city).data
        self.assertIn('latitude', data)
        self.assertIn('longitude', data)
        self.assertIsNone(data['latitude'])
        self.assertIsNone(data['longitude'])

    def test_region_serializer_falls_back_to_country_centroid(self):
        vatican = Country.objects.create(
            name='Vatican City State (Holy See)',
            country_code='VA',
            coordinates=make_point(12.453389, 41.902916),
        )
        region = Region.objects.create(
            id='VA-00',
            name='Vatican City State (Holy See)',
            country=vatican,
            coordinates=None,
        )
        data = RegionSerializer(region).data
        self.assertAlmostEqual(data['latitude'], 41.902916, places=4)
        self.assertAlmostEqual(data['longitude'], 12.453389, places=4)

    def test_visited_region_serializer_falls_back_to_country_centroid(self):
        from users.models import CustomUser
        from worldtravel.models import VisitedRegion
        from worldtravel.serializers import VisitedRegionSerializer

        vatican = Country.objects.create(
            name='Vatican City State (Holy See)',
            country_code='VA',
            coordinates=make_point(12.453389, 41.902916),
        )
        region = Region.objects.create(
            id='VA-00',
            name='Vatican City State (Holy See)',
            country=vatican,
            coordinates=None,
        )
        user = CustomUser.objects.create_user(
            username='vatican-visitor',
            email='vatican-visitor@example.com',
            password='testpassword123',
        )
        visit = VisitedRegion.objects.create(user=user, region=region)
        data = VisitedRegionSerializer(visit).data
        self.assertAlmostEqual(data['latitude'], 41.902916, places=4)
        self.assertAlmostEqual(data['longitude'], 12.453389, places=4)
        self.assertEqual(data['name'], 'Vatican City State (Holy See)')

    def test_region_null_island_falls_back_to_country_centroid(self):
        vatican = Country.objects.create(
            name='Vatican City State (Holy See)',
            country_code='VA',
            coordinates=make_point(12.453389, 41.902916),
        )
        region = Region.objects.create(
            id='VA-00',
            name='Vatican City State (Holy See)',
            country=vatican,
            coordinates=make_point(0, 0),
        )
        data = RegionSerializer(region).data
        self.assertAlmostEqual(data['latitude'], 41.902916, places=4)
        self.assertAlmostEqual(data['longitude'], 12.453389, places=4)
