from rest_framework import serializers
from django.contrib.auth import get_user_model

from adventures.models import Collection, CollectionInvite

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
from main.utils import build_media_url

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
        extra_fields = ['profile_pic', 'uuid', 'public_profile']

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
        if hasattr(UserModel, 'default_currency'):
            extra_fields.append('default_currency')
        if hasattr(UserModel, 'map_style'):
            extra_fields.append('map_style')

        fields = ['pk', *extra_fields]
        read_only_fields = ('email', 'date_joined', 'is_staff', 'is_superuser', 'is_active', 'pk', 'disable_password')

    def handle_public_profile_change(self, instance, validated_data):
        """
        Leaving shared collections when a profile becomes private is intentional:
        private profiles are not discoverable for new shares, and collaborators
        should not retain access through a relationship that started via public discovery.
        """
        if 'public_profile' in validated_data and not validated_data['public_profile']:
            shared_collections = list(Collection.objects.filter(shared_with=instance))
            left_count = len(shared_collections)
            for collection in shared_collections:
                collection.shared_with.remove(instance)

            pending_invites = CollectionInvite.objects.filter(invited_user=instance)
            invite_count = pending_invites.count()
            pending_invites.delete()

            self._sharing_impact = {
                'left_shared_collections': left_count,
                'revoked_collection_invites': invite_count,
            }
        else:
            self._sharing_impact = None

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
    shared_collection_count = serializers.SerializerMethodField()
    pending_collection_invite_count = serializers.SerializerMethodField()

    class Meta(UserDetailsSerializer.Meta):
        model = CustomUser
        fields = UserDetailsSerializer.Meta.fields + [
            'has_password',
            'disable_password',
            'shared_collection_count',
            'pending_collection_invite_count',
        ]
        read_only_fields = UserDetailsSerializer.Meta.read_only_fields + (
            'uuid',
            'has_password',
            'disable_password',
            'shared_collection_count',
            'pending_collection_invite_count',
        )

    @staticmethod
    def get_shared_collection_count(instance):
        return Collection.objects.filter(shared_with=instance).count()

    @staticmethod
    def get_pending_collection_invite_count(instance):
        return CollectionInvite.objects.filter(invited_user=instance).count()

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
            representation['profile_pic'] = build_media_url(instance.profile_pic.name)

        # Remove `pk` field from the response
        representation.pop('pk', None)
        # Remove the email field
        representation.pop('email', None)

        sharing_impact = getattr(self, '_sharing_impact', None)
        if sharing_impact:
            representation.update(sharing_impact)

        return representation


from .models import APIKey


class APIKeySerializer(serializers.ModelSerializer):
    """
    Read serializer for APIKey – never exposes the key_hash or the raw token.
    The raw token is injected by the view only at creation time via an extra
    ``key`` field that is *not* part of the model serializer.
    """

    class Meta:
        model = APIKey
        fields = ['id', 'name', 'key_prefix', 'created_at', 'last_used_at']
        read_only_fields = ['id', 'key_prefix', 'created_at', 'last_used_at']


class APIKeyCreateSerializer(serializers.Serializer):
    """Write serializer – only accepts a ``name`` for the new key."""

    name = serializers.CharField(max_length=100, required=True)
