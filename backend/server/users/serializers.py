from rest_framework import serializers
from django.contrib.auth import get_user_model

from adventures.models import Collection
from dj_rest_auth.serializers import PasswordResetSerializer

User = get_user_model()

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

try:
    from allauth.account import app_settings as allauth_account_settings
    from allauth.account.adapter import get_adapter
    from allauth.account.utils import setup_user_email
    from allauth.socialaccount.models import EmailAddress
    from allauth.utils import get_username_max_length
except ImportError:
    raise ImportError('allauth needs to be added to INSTALLED_APPS.')

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
from dj_rest_auth.serializers import UserDetailsSerializer
from .models import CustomUser

from rest_framework import serializers
from django.conf import settings
import os

class UserDetailsSerializer(serializers.ModelSerializer):
    """
    User model w/o password
    """

    @staticmethod
    def validate_username(username):
        if 'allauth.account' not in settings.INSTALLED_APPS:
            return username

        from allauth.account.adapter import get_adapter
        username = get_adapter().clean_username(username.lower())  # Convert username to lowercase
        return username

    class Meta:
        extra_fields = ['profile_pic', 'uuid', 'public_profile']
        profile_pic = serializers.ImageField(required=False)

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
        if hasattr(UserModel, 'public_profile'):
            extra_fields.append('public_profile')

        class Meta(UserDetailsSerializer.Meta):
            model = CustomUser
            fields = UserDetailsSerializer.Meta.fields + ('profile_pic', 'uuid', 'public_profile')

        model = UserModel
        fields = ('pk', *extra_fields)
        read_only_fields = ('email', 'date_joined', 'is_staff', 'is_superuser', 'is_active', 'pk')

    def handle_public_profile_change(self, instance, validated_data):
        """Remove user from `shared_with` if public profile is set to False."""
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


    class Meta(UserDetailsSerializer.Meta):
        model = CustomUser
        fields = UserDetailsSerializer.Meta.fields + ('profile_pic', 'uuid', 'public_profile')
        read_only_fields = UserDetailsSerializer.Meta.read_only_fields + ('uuid',)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.profile_pic:
            public_url = os.environ.get('PUBLIC_URL', 'http://127.0.0.1:8000').rstrip('/')
            #print(public_url)
            # remove any  ' from the url
            public_url = public_url.replace("'", "")
            representation['profile_pic'] = f"{public_url}/media/{instance.profile_pic.name}"
        del representation['pk'] # remove the pk field from the response
        return representation
