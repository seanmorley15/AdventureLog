from .models import Country, Region, VisitedRegion
from rest_framework import serializers


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'  # Serialize all fields of the Adventure model

class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = '__all__'  # Serialize all fields of the Adventure model

class VisitedRegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitedRegion
        fields = '__all__'  # Serialize all fields of the Adventure model