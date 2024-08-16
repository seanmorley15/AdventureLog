from rest_framework import serializers
from django.contrib.auth import get_user_model

from adventures.models import Adventure
from users.forms import CustomAllAuthPasswordResetForm
from dj_rest_auth.serializers import PasswordResetSerializer
from rest_framework.exceptions import PermissionDenied

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
    

class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=get_username_max_length(),
        min_length=allauth_account_settings.USERNAME_MIN_LENGTH,
        required=allauth_account_settings.USERNAME_REQUIRED,
    )
    email = serializers.EmailField(required=allauth_account_settings.EMAIL_REQUIRED)
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)

    def validate_username(self, username):
        username = get_adapter().clean_username(username)
        return username

    def validate_email(self, email):
        email = get_adapter().clean_email(email)
        if allauth_account_settings.UNIQUE_EMAIL:
            if email and EmailAddress.objects.is_verified(email):
                raise serializers.ValidationError(
                    _('A user is already registered with this e-mail address.'),
                )
        return email

    def validate_password1(self, password):
        return get_adapter().clean_password(password)

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError(_("The two password fields didn't match."))
        return data

    def custom_signup(self, request, user):
        pass

    def get_cleaned_data(self):
        return {
            'username': self.validated_data.get('username', ''),
            'password1': self.validated_data.get('password1', ''),
            'email': self.validated_data.get('email', ''),
            'first_name': self.validated_data.get('first_name', ''),
            'last_name': self.validated_data.get('last_name', ''),
        }

    def save(self, request):
        # Check if registration is disabled
        if getattr(settings, 'DISABLE_REGISTRATION', False):
            raise PermissionDenied("Registration is currently disabled.")

        # If registration is not disabled, proceed with the original logic
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()
        user = adapter.save_user(request, user, self, commit=False)
        if "password1" in self.cleaned_data:
            try:
                adapter.clean_password(self.cleaned_data['password1'], user=user)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(
                    detail=serializers.as_serializer_error(exc)
                )
        user.save()
        self.custom_signup(request, user)
        setup_user_email(request, user, [])
        return user

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

# class AdventureSerializer(serializers.ModelSerializer):
#     image = serializers.SerializerMethodField()

#     class Meta:
#         model = Adventure
#         fields = ['id', 'user_id', 'type', 'name', 'location', 'activity_types', 'description', 
#                   'rating', 'link', 'image', 'date', 'trip_id', 'is_public', 'longitude', 'latitude']

#     def get_image(self, obj):
#         if obj.image:
#             public_url = os.environ.get('PUBLIC_URL', '')
#             return f'{public_url}/media/{obj.image.name}'
#         return None

class UserDetailsSerializer(serializers.ModelSerializer):
    """
    User model w/o password
    """

    @staticmethod
    def validate_username(username):
        if 'allauth.account' not in settings.INSTALLED_APPS:
            # We don't need to call the all-auth
            # username validator unless it's installed
            return username

        from allauth.account.adapter import get_adapter
        username = get_adapter().clean_username(username)
        return username

    class Meta:
        extra_fields = ['profile_pic']
        profile_pic = serializers.ImageField(required=False)
        # see https://github.com/iMerica/dj-rest-auth/issues/181
        # UserModel.XYZ causing attribute error while importing other
        # classes from `serializers.py`. So, we need to check whether the auth model has
        # the attribute or not
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

        class Meta(UserDetailsSerializer.Meta):
            model = CustomUser
            fields = UserDetailsSerializer.Meta.fields + ('profile_pic',)
            
        model = UserModel
        fields = ('pk', *extra_fields)
        read_only_fields = ('email', 'date_joined', 'is_staff', 'is_superuser', 'is_active', 'pk')

class CustomUserDetailsSerializer(UserDetailsSerializer):


    class Meta(UserDetailsSerializer.Meta):
        model = CustomUser
        fields = UserDetailsSerializer.Meta.fields + ('profile_pic',)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.profile_pic:
            public_url = os.environ.get('PUBLIC_URL', 'http://127.0.0.1:8000').rstrip('/')
            #print(public_url)
            # remove any  ' from the url
            public_url = public_url.replace("'", "")
            representation['profile_pic'] = f"{public_url}/media/{instance.profile_pic.name}"
        return representation

class MyPasswordResetSerializer(PasswordResetSerializer):

    def validate_email(self, value):
        # use the custom reset form
        self.reset_form = CustomAllAuthPasswordResetForm(data=self.initial_data)
        if not self.reset_form.is_valid():
            raise serializers.ValidationError(self.reset_form.errors)

        return value