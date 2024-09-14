import os
from .models import Country, Region, VisitedRegion
from rest_framework import serializers

class CountrySerializer(serializers.ModelSerializer):
    def get_public_url(self, obj):
        return os.environ.get('PUBLIC_URL', 'http://127.0.0.1:8000').rstrip('/').replace("'", "")

    flag_url = serializers.SerializerMethodField()

    def get_flag_url(self, obj):
        public_url = self.get_public_url(obj)
        return public_url + '/media/' + 'flags/' + obj.country_code.lower() + '.png'

    class Meta:
        model = Country
        fields = '__all__'
        read_only_fields = ['id', 'name', 'country_code', 'subregion', 'flag_url']

class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = '__all__'
        read_only_fields = ['id', 'name', 'country', 'longitude', 'latitude']

class VisitedRegionSerializer(serializers.ModelSerializer):
    longitude = serializers.DecimalField(source='region.longitude', max_digits=9, decimal_places=6, read_only=True)
    latitude = serializers.DecimalField(source='region.latitude', max_digits=9, decimal_places=6, read_only=True)
    name = serializers.CharField(source='region.name', read_only=True)

    class Meta:
        model = VisitedRegion
        fields = ['id', 'user_id', 'region', 'longitude', 'latitude', 'name']
        read_only_fields = ['user_id', 'id', 'longitude', 'latitude', 'name']