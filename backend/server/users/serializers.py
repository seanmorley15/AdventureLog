from rest_framework import serializers
from django.contrib.auth import get_user_model

from adventures.models import Collection

User = get_user_model()

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class ChangeEmailSerializer(serializers.Serializer):
    new_email = serializers.EmailField(required=True)

    def validate_new_email(self, value):
        user = self.context['request'].user
        if User.objects.filter(email=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value
    



from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
UserModel = get_user_model()
# from dj_rest_auth.serializers import UserDetailsSerializer
from .models import CustomUser

from rest_framework import serializers
from django.conf import settings
import os

class UserDetailsSerializer(serializers.ModelSerializer):
    """
    User model without exposing the password.
    """

    @staticmethod
    def validate_username(username):
        if 'allauth.account' not in settings.INSTALLED_APPS:
            return username

        from allauth.account.adapter import get_adapter
        username = get_adapter().clean_username(username.lower())  # Convert username to lowercase
        return username

    class Meta:
        model = CustomUser
        extra_fields = ['profile_pic', 'uuid', 'public_profile', 'measurement_system']

        if hasattr(UserModel, 'USERNAME_FIELD'):
            extra_fields.append(UserModel.USERNAME_FIELD)
        if hasattr(UserModel, 'EMAIL_FIELD'):
            extra_fields.append(UserModel.EMAIL_FIELD)
        if hasattr(UserModel, 'first_name'):
            extra_fields.append('first_name')
        if hasattr(UserModel, 'last_name'):
            extra_fields.append('last_name')
        if hasattr(UserModel, 'date_joined'):
            extra_fields.append('date_joined')
        if hasattr(UserModel, 'is_staff'):
            extra_fields.append('is_staff')
        if hasattr(UserModel, 'disable_password'):
            extra_fields.append('disable_password')
        if hasattr(UserModel, 'measurement_system'):
            extra_fields.append('measurement_system')

        fields = ['pk', *extra_fields]
        read_only_fields = ('email', 'date_joined', 'is_staff', 'is_superuser', 'is_active', 'pk', 'disable_password')

    def handle_public_profile_change(self, instance, validated_data):
        """
        Remove user from `shared_with` if public profile is set to False.
        """
        if 'public_profile' in validated_data and not validated_data['public_profile']:
            for collection in Collection.objects.filter(shared_with=instance):
                collection.shared_with.remove(instance)

    def update(self, instance, validated_data):
        self.handle_public_profile_change(instance, validated_data)
        return super().update(instance, validated_data)

    def partial_update(self, instance, validated_data):
        self.handle_public_profile_change(instance, validated_data)
        return super().partial_update(instance, validated_data)


class CustomUserDetailsSerializer(UserDetailsSerializer):
    """
    Custom serializer to add additional fields and logic for the user details.
    """

    has_password = serializers.SerializerMethodField()

    class Meta(UserDetailsSerializer.Meta):
        model = CustomUser
        fields = UserDetailsSerializer.Meta.fields + ['profile_pic', 'uuid', 'public_profile', 'has_password', 'disable_password', 'measurement_system']
        read_only_fields = UserDetailsSerializer.Meta.read_only_fields + ('uuid', 'has_password', 'disable_password')

    @staticmethod
    def get_has_password(instance):
        """
        Computes whether the user has a usable password set.
        """
        return instance.has_usable_password()

    def to_representation(self, instance):
        """
        Customizes the serialized output to modify `profile_pic` URL and add computed fields.
        """
        representation = super().to_representation(instance)

        # Construct profile picture URL if it exists
        if instance.profile_pic:
            public_url = os.environ.get('PUBLIC_URL', 'http://127.0.0.1:8000').rstrip('/')
            public_url = public_url.replace("'", "")  # Sanitize URL
            representation['profile_pic'] = f"{public_url}/media/{instance.profile_pic.name}"

        # Remove `pk` field from the response
        representation.pop('pk', None)
        # Remove the email field
        representation.pop('email', None)
        
        return representation
