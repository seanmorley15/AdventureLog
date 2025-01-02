from .models import ImmichIntegration
from rest_framework import serializers

class ImmichIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImmichIntegration
        fields = '__all__'
        read_only_fields = ['id', 'user']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation.pop('user', None)
        return representation
