from .models import Country, Region, VisitedRegion, City, VisitedCity
from rest_framework import serializers
from main.utils import CustomModelSerializer, build_media_url


class CountrySerializer(serializers.ModelSerializer):
    flag_url = serializers.SerializerMethodField()
    num_regions = serializers.SerializerMethodField()
    num_visits = serializers.SerializerMethodField()

    def get_flag_url(self, obj):
        flag_path = f"flags/{obj.country_code.lower()}.png"
        return build_media_url(flag_path)
    
    def get_num_regions(self, obj):
        # get the number of regions in the country
        return Region.objects.filter(country=obj).count()
    
    def get_num_visits(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        
        if user and user.is_authenticated:
            return VisitedRegion.objects.filter(region__country=obj, user=user).count()
        
        return 0

    class Meta:
        model = Country
        fields = '__all__'
        read_only_fields = ['id', 'name', 'country_code', 'subregion', 'flag_url', 'num_regions', 'num_visits', 'longitude', 'latitude', 'capital']


class RegionSerializer(serializers.ModelSerializer):
    num_cities = serializers.SerializerMethodField()
    country_name = serializers.CharField(source='country.name', read_only=True)
    class Meta:
        model = Region
        fields = '__all__'
        read_only_fields = ['id', 'name', 'country', 'longitude', 'latitude', 'num_cities', 'country_name']

    def get_num_cities(self, obj):
        return City.objects.filter(region=obj).count()

class CitySerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source='region.name', read_only=True)
    country_name = serializers.CharField(source='region.country.name', read_only=True
    )
    class Meta:
        model = City
        fields = '__all__'
        read_only_fields = ['id', 'name', 'region', 'longitude', 'latitude', 'region_name', 'country_name']

class VisitedRegionSerializer(CustomModelSerializer):
    longitude = serializers.DecimalField(source='region.longitude', max_digits=9, decimal_places=6, read_only=True)
    latitude = serializers.DecimalField(source='region.latitude', max_digits=9, decimal_places=6, read_only=True)
    name = serializers.CharField(source='region.name', read_only=True)

    class Meta:
        model = VisitedRegion
        fields = ['id', 'user', 'region', 'longitude', 'latitude', 'name']
        read_only_fields = ['user', 'id', 'longitude', 'latitude', 'name']

class VisitedCitySerializer(CustomModelSerializer):
    longitude = serializers.DecimalField(source='city.longitude', max_digits=9, decimal_places=6, read_only=True)
    latitude = serializers.DecimalField(source='city.latitude', max_digits=9, decimal_places=6, read_only=True)
    name = serializers.CharField(source='city.name', read_only=True)

    class Meta:
        model = VisitedCity
        fields = ['id', 'user', 'city', 'longitude', 'latitude', 'name']
        read_only_fields = ['user', 'id', 'longitude', 'latitude', 'name']