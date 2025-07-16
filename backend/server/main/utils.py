from rest_framework import serializers

def get_user_uuid(user):
    return str(user.uuid)

class CustomModelSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user'] = get_user_uuid(instance.user)
        return representation