from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from django.contrib.auth import get_user_model
from django.conf import settings
from adventures.models import Collection, CollectionInvite
from core.public_url import build_media_url
from .models import CustomUser, APIKey

User = get_user_model()
UserModel = get_user_model()


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
        if hasattr(UserModel, 'date_format'):
            extra_fields.append('date_format')
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
        # `pk` and `email` are never sent (see to_representation); emails are managed through allauth.
        fields = [f for f in UserDetailsSerializer.Meta.fields if f not in ('pk', 'email')] + [
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
    @extend_schema_field(serializers.IntegerField())
    def get_shared_collection_count(instance):
        return Collection.objects.filter(shared_with=instance).count()

    @staticmethod
    @extend_schema_field(serializers.IntegerField())
    def get_pending_collection_invite_count(instance):
        return CollectionInvite.objects.filter(invited_user=instance).count()

    @staticmethod
    @extend_schema_field(serializers.BooleanField())
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


# Account details that belong to the signed-in user only. Anyone else's view of a person omits them.
PRIVATE_USER_FIELDS = (
    'has_password',
    'disable_password',
    'shared_collection_count',
    'pending_collection_invite_count',
)


def without_private_fields(data):
    """A copy of serialized user data without the fields only the user themselves should see."""
    return {key: value for key, value in data.items() if key not in PRIVATE_USER_FIELDS}


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


class DeleteAccountSerializer(serializers.Serializer):
    """Validates account-deletion confirmation and optional password re-auth."""

    confirmation = serializers.CharField(required=True)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user
        confirmation = attrs.get("confirmation", "").strip()

        if confirmation != user.username:
            raise serializers.ValidationError(
                {"confirmation": "Type your username exactly to confirm account deletion."}
            )

        if user.has_usable_password() and not user.disable_password:
            password = attrs.get("password", "")
            if not password:
                raise serializers.ValidationError(
                    {"password": "Password is required to delete your account."}
                )
            if not user.check_password(password):
                raise serializers.ValidationError({"password": "Incorrect password."})

        return attrs


class PublicProfileSerializer(CustomUserDetailsSerializer):
    """A user as anyone else sees them: the account-only fields are left out."""

    class Meta(CustomUserDetailsSerializer.Meta):
        fields = [f for f in CustomUserDetailsSerializer.Meta.fields if f not in PRIVATE_USER_FIELDS]


class APIKeyCreatedSerializer(APIKeySerializer):
    key = serializers.CharField(
        read_only=True,
        help_text='The full key. It is returned only in this response and cannot be shown again.',
    )

    class Meta(APIKeySerializer.Meta):
        fields = APIKeySerializer.Meta.fields + ['key']


class MobileKeySerializer(APIKeyCreatedSerializer):
    qr_code = serializers.CharField(
        read_only=True,
        help_text='A PNG data URI of a QR code holding the server URL and the key, for the mobile app to scan.',
    )

    class Meta(APIKeyCreatedSerializer.Meta):
        fields = APIKeyCreatedSerializer.Meta.fields + ['qr_code']


class MediaUsageSerializer(serializers.Serializer):
    total_bytes = serializers.IntegerField()
    images_bytes = serializers.IntegerField()
    attachments_bytes = serializers.IntegerField()
    profile_pics_bytes = serializers.IntegerField()
    images_files = serializers.IntegerField()
    attachments_files = serializers.IntegerField()
    profile_pics_files = serializers.IntegerField()
    limit_bytes = serializers.IntegerField(
        allow_null=True, help_text='The storage limit for the account, or null when there is none.'
    )


class PasswordLoginSerializer(serializers.Serializer):
    disable_password = serializers.BooleanField(
        help_text='True when signing in with a password is turned off for this account.'
    )


class _RegistrationSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    message = serializers.CharField(allow_blank=True, allow_null=True, help_text='Shown when sign-up is closed.')


class _PasswordPolicySerializer(serializers.Serializer):
    min_length = serializers.IntegerField()
    validators_enabled = serializers.BooleanField(
        help_text="True when Django's password strength checks (common, numeric, similar) are on."
    )


class _LegalLinksSerializer(serializers.Serializer):
    terms_of_service_url = serializers.URLField(allow_null=True)
    privacy_policy_url = serializers.URLField(allow_null=True)


class _SocialProviderSerializer(serializers.Serializer):
    provider = serializers.CharField(help_text='e.g. `github`, `openid_connect`.')
    name = serializers.CharField()
    url = serializers.URLField(help_text='Open this in the browser to sign in with the provider.')
    usage_required = serializers.BooleanField(help_text='True when password sign-in is disabled on this server.')


class AuthConfigSerializer(serializers.Serializer):
    registration = _RegistrationSerializer()
    password_policy = _PasswordPolicySerializer()
    legal_links = _LegalLinksSerializer()
    social_providers = _SocialProviderSerializer(many=True)


class CsrfTokenSerializer(serializers.Serializer):
    csrf_token = serializers.CharField(help_text='Send as `X-CSRFToken` on requests that change data.')


class InviteStatusSerializer(serializers.Serializer):
    valid = serializers.BooleanField()
    email = serializers.EmailField(allow_null=True)
    expired = serializers.BooleanField()
    accepted = serializers.BooleanField()
    registered = serializers.BooleanField(help_text='True when an account with this email already exists.')
    message = serializers.CharField(
        allow_null=True, help_text='Why the invite cannot be used: `invalid`, `expired`, `already_accepted` or `already_registered`.'
    )


class AccountSerializer(serializers.Serializer):
    user = CustomUserDetailsSerializer()
    pending_invite_count = serializers.IntegerField(help_text='Collection invites waiting for an answer.')
    unread_comment_count = serializers.IntegerField(help_text='Comments in your inbox you have not seen.')


class UserStatsSerializer(serializers.Serializer):
    location_count = serializers.IntegerField()
    visited_location_count = serializers.IntegerField()
    trips_count = serializers.IntegerField(help_text='Collections the user owns.')
    visited_city_count = serializers.IntegerField()
    total_cities = serializers.IntegerField()
    visited_region_count = serializers.IntegerField()
    total_regions = serializers.IntegerField()
    visited_country_count = serializers.IntegerField()
    total_countries = serializers.IntegerField()
    activities_overall = serializers.DictField(
        help_text='Totals over all activities: `total_count`, `total_distance` (m), '
        '`total_moving_time` (s), `total_elevation_gain` (m) and more.'
    )
    activity_distance = serializers.FloatField(help_text='Total distance in meters.')
    activity_moving_time = serializers.FloatField(help_text='Total moving time in seconds.')
    activity_elevation = serializers.FloatField(help_text='Total elevation gain in meters.')
    activity_count = serializers.IntegerField()
    activities_by_category = serializers.JSONField(help_text='The same totals per sport category.')
