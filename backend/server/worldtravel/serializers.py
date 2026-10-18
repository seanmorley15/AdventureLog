from .models import Country, Region, VisitedRegion, City, VisitedCity
from rest_framework import serializers
from main.utils import CustomModelSerializer, build_media_url, memoized_count
from adventures.utils.geo import point_to_lat_lon


class ReadOnlyLatLonMixin:
    """Expose a model `coordinates` PointField as read-only latitude/longitude."""

    def to_representation(self, instance):
        data = super().to_representation(instance)
        lat, lon = point_to_lat_lon(instance.coordinates)
        data['latitude'] = lat
        data['longitude'] = lon
        return data


class CountrySerializer(ReadOnlyLatLonMixin, serializers.ModelSerializer):
    flag_url = serializers.SerializerMethodField()
    num_regions = serializers.SerializerMethodField()
    num_visits = serializers.SerializerMethodField()

    def get_flag_url(self, obj):
        flag_path = f"flags/{obj.country_code.lower()}.png"
        return build_media_url(flag_path)
    
    def get_num_regions(self, obj):
        # Annotated by the viewsets that list countries; per-row count otherwise.
        if hasattr(obj, 'num_regions_annotated'):
            return obj.num_regions_annotated
        return memoized_count(self, 'country_regions', obj.pk, lambda: Region.objects.filter(country=obj).count())
    
    def get_num_visits(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        
        if hasattr(obj, 'num_visits_annotated'):
            return obj.num_visits_annotated

        if user and user.is_authenticated:
            return memoized_count(
                self,
                'country_visits',
                (obj.pk, user.pk),
                lambda: VisitedRegion.objects.filter(region__country=obj, user=user).count(),
            )
        
        return 0

    class Meta:
        model = Country
        exclude = ['coordinates']
        read_only_fields = ['id', 'name', 'country_code', 'subregion', 'flag_url', 'num_regions', 'num_visits', 'longitude', 'latitude', 'capital']


class RegionSerializer(ReadOnlyLatLonMixin, serializers.ModelSerializer):
    num_cities = serializers.SerializerMethodField()
    country_name = serializers.CharField(source='country.name', read_only=True)
    class Meta:
        model = Region
        exclude = ['coordinates']
        read_only_fields = ['id', 'name', 'country', 'longitude', 'latitude', 'num_cities', 'country_name']

    def get_num_cities(self, obj):
        if hasattr(obj, 'num_cities_annotated'):
            return obj.num_cities_annotated
        return memoized_count(self, 'region_cities', obj.pk, lambda: City.objects.filter(region=obj).count())

    def to_representation(self, instance):
        data = super().to_representation(instance)
        lat, lon = instance.resolved_lat_lon()
        data['latitude'] = lat
        data['longitude'] = lon
        return data

class CitySerializer(ReadOnlyLatLonMixin, serializers.ModelSerializer):
    region_name = serializers.CharField(source='region.name', read_only=True)
    country_name = serializers.CharField(source='region.country.name', read_only=True
    )
    class Meta:
        model = City
        exclude = ['coordinates']
        read_only_fields = ['id', 'name', 'region', 'longitude', 'latitude', 'region_name', 'country_name']

class VisitedRegionSerializer(CustomModelSerializer):
    longitude = serializers.FloatField(source='region.longitude', read_only=True, allow_null=True)
    latitude = serializers.FloatField(source='region.latitude', read_only=True, allow_null=True)
    name = serializers.CharField(source='region.name', read_only=True)

    class Meta:
        model = VisitedRegion
        fields = ['id', 'user', 'region', 'longitude', 'latitude', 'name']
        read_only_fields = ['user', 'id', 'longitude', 'latitude', 'name']

class VisitedCitySerializer(CustomModelSerializer):
    longitude = serializers.FloatField(source='city.longitude', read_only=True, allow_null=True)
    latitude = serializers.FloatField(source='city.latitude', read_only=True, allow_null=True)
    name = serializers.CharField(source='city.name', read_only=True)

    class Meta:
        model = VisitedCity
        fields = ['id', 'user', 'city', 'longitude', 'latitude', 'name']
        read_only_fields = ['user', 'id', 'longitude', 'latitude', 'name']