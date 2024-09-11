import os
from .models import Country, Region, VisitedRegion
from rest_framework import serializers


class CountrySerializer(serializers.ModelSerializer):
    def get_public_url(self, obj):
        return os.environ.get('PUBLIC_URL', 'http://127.0.0.1:8000').rstrip('/').replace("'", "")

    flag_url = serializers.SerializerMethodField()

    def get_flag_url(self, obj):
        public_url = self.get_public_url(obj)
        return public_url + '/media/' + 'flags/' + obj.country_code + '.png'

    class Meta:
        model = Country
        fields = '__all__'  # Serialize all fields of the Adventure model
        read_only_fields = ['id', 'name', 'country_code', 'subregion', 'flag_url']

class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = '__all__'  # Serialize all fields of the Adventure model
        read_only_fields = ['id', 'name', 'country', 'longitude', 'latitude']

class VisitedRegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitedRegion
        fields = '__all__'  # Serialize all fields of the Adventure model
        read_only_fields = ['user_id', 'id']