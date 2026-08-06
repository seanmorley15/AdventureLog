from .models import EndurainIntegration, ImmichIntegration, WandererIntegration
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


class EndurainIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EndurainIntegration
        fields = ['id', 'server_url', 'username', 'auth_method', 'endurain_user_id']
        read_only_fields = ['id', 'username', 'auth_method', 'endurain_user_id']

    def to_representation(self, instance):
        return {
            'id': str(instance.id),
            'server_url': instance.server_url,
            'username': instance.username,
            'auth_method': instance.auth_method,
            'endurain_user_id': instance.endurain_user_id,
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
