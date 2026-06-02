from .models import ImmichIntegration, WandererIntegration
from rest_framework import serializers


class WandererIntegrationSerializer(serializers.ModelSerializer):
    api_key = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = WandererIntegration
        fields = ['id', 'server_url', 'api_key']
        read_only_fields = ['id']

    def to_representation(self, instance):
        return {
            'id': str(instance.id),
            'server_url': instance.server_url,
        }


class ImmichIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImmichIntegration
        fields = '__all__'
        read_only_fields = ['id', 'user']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation.pop('user', None)
        return representation
