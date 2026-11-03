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
        fields = ['id', 'server_url', 'api_key', 'copy_locally']
        read_only_fields = ['id']
        # The key is accepted on create/update but never sent back to the client.
        extra_kwargs = {
            'api_key': {'write_only': True},
            'server_url': {'help_text': 'Your Immich address, e.g. `https://photos.example.com`. `/api` is found.'},
        }


class ImmichSearchQuerySerializer(serializers.Serializer):
    query = serializers.CharField(required=False, help_text='Smart (CLIP) search text.')
    date = serializers.DateField(required=False, help_text='Photos taken on this day.')

    def validate(self, attrs):
        if not attrs.get('query') and not attrs.get('date'):
            raise serializers.ValidationError('Send query or date.')
        return attrs


class ImmichAssetSerializer(serializers.Serializer):
    """An Immich asset as Immich returns it, plus the address to show it through AdventureLog."""

    id = serializers.CharField()
    image_url = serializers.URLField(help_text='A preview served through this server, usable in `<img>`.')
    originalFileName = serializers.CharField(required=False)
    fileCreatedAt = serializers.DateTimeField(required=False)
    exifInfo = serializers.DictField(required=False)


class IntegrationStatusSerializer(serializers.Serializer):
    immich = serializers.DictField(help_text='`{exists, copy_locally}`')
    google_maps = serializers.BooleanField(help_text='Whether the server has a Google Maps key.')
    strava = serializers.DictField(help_text='`{global, user}`: the server can use Strava; you connected it.')
    wanderer = serializers.DictField(help_text='`{exists}`')
    endurain = serializers.DictField(help_text='`{exists}`')
