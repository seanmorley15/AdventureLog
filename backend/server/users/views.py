from os import getenv
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import ChangeEmailSerializer, APIKeySerializer, APIKeyCreateSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .serializers import CustomUserDetailsSerializer as PublicUserSerializer
from allauth.socialaccount.models import SocialApp
from adventures.serializers import LocationSerializer, CollectionSerializer
from adventures.models import Location, Collection
from allauth.socialaccount.models import SocialAccount
from .models import APIKey
import qrcode
import io
import base64
import json
from datetime import datetime

User = get_user_model()

class ChangeEmailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=ChangeEmailSerializer,
        responses={
            200: openapi.Response('Email successfully changed'),
            400: 'Bad Request'
        },
        operation_description="Change the email address for the authenticated user."
    )
    def post(self, request):
        serializer = ChangeEmailSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            new_email = serializer.validated_data['new_email']
            user.email = new_email
            # remove all other email addresses for the user
            user.emailaddress_set.exclude(email=new_email).delete()
            user.emailaddress_set.create(email=new_email, primary=True, verified=False)
            user.save()
            return Response({"detail": "Email successfully changed."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class IsRegistrationDisabled(APIView):
    # This endpoint is requested on auth pages and should not be globally throttled.
    # A 429 here can break signup UX even for legitimate users.
    throttle_classes = []

    @swagger_auto_schema(
        responses={
            200: openapi.Response('Registration is disabled'),
            400: 'Bad Request'
        },
        operation_description="Check if registration is disabled."
    )
    def get(self, request):
        return Response({"is_disabled": settings.DISABLE_REGISTRATION, "message": settings.DISABLE_REGISTRATION_MESSAGE}, status=status.HTTP_200_OK)

class PublicUserListView(APIView):
    # Allow the listing of all public users
    permission_classes = []

    @swagger_auto_schema(
        responses={
            200: openapi.Response('List of public users'),
            400: 'Bad Request'
        },
        operation_description="List public users."
    )
    def get(self, request):
        users = User.objects.filter(public_profile=True).exclude(id=request.user.id)
        # remove the email addresses from the response
        for user in users:
            user.email = None
        serializer = PublicUserSerializer(users, many=True)
        # for every user, remove the field has_password
        for user in serializer.data:
            user.pop('has_password', None)
            user.pop('disable_password', None)
        return Response(serializer.data, status=status.HTTP_200_OK)

class PublicUserDetailView(APIView):
    # Allow the retrieval of a single public user
    permission_classes = []

    @swagger_auto_schema(
        responses={
            200: openapi.Response('Public user information'),
            400: 'Bad Request'
        },
        operation_description="Get public user information."
    )
    def get(self, request, username):
        if request.user.username == username:
            user = get_object_or_404(User, username=username)
        else:
            user = get_object_or_404(User, username=username, public_profile=True)
        serializer = PublicUserSerializer(user)
        # for every user, remove the field has_password
        serializer.data.pop('has_password', None)
        
        # remove the email address from the response
        user.email = None
        
        # Get the users adventures and collections to include in the response
        adventures = Location.objects.filter(user=user, is_public=True)
        collections = Collection.objects.filter(user=user, is_public=True)
        adventure_serializer = LocationSerializer(adventures, many=True)
        collection_serializer = CollectionSerializer(collections, many=True)

        return Response({
            'user': serializer.data,
            'adventures': adventure_serializer.data,
            'collections': collection_serializer.data
        }, status=status.HTTP_200_OK)

class UserMetadataView(APIView):
    permission_classes = [IsAuthenticated]
    # This endpoint is used by the frontend auth hook to hydrate user state.
    # Global throttling can cause an auth loop and forced logout behavior.
    throttle_classes = []

    @swagger_auto_schema(
        responses={
            200: openapi.Response('User metadata'),
            400: 'Bad Request'
        },
        operation_description="Get user metadata."
    )
    def get(self, request):
        user = request.user
        serializer = PublicUserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class UpdateUserMetadataView(APIView):
    """
    Update user metadata using fields from the PublicUserSerializer.
    Using patch opposed to put allows for partial updates, covers the case where it checks the username and says it's already taken. Duplicate uesrname values should not be included in the request to avoid this.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=PublicUserSerializer,
        responses={
            200: openapi.Response('User metadata updated'),
            400: 'Bad Request'
        },
        operation_description="Update user metadata."
    )
    def patch(self, request):
        user = request.user
        serializer = PublicUserSerializer(user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class EnabledSocialProvidersView(APIView):
    """
    Get enabled social providers for social authentication. This is used to determine which buttons to show on the frontend. Also returns a URL for each to start the authentication flow.
    """

    @swagger_auto_schema(
        responses={
            200: openapi.Response('Enabled social providers'),
            400: 'Bad Request'
        },
        operation_description="Get enabled social providers."
    )
    def get(self, request):
        social_providers = SocialApp.objects.filter(sites=settings.SITE_ID)
        providers = []
        for provider in social_providers:
            if provider.provider == 'openid_connect':
                new_provider = f'oidc/{provider.provider_id}'
            else:
                new_provider = provider.provider
            providers.append({
                'provider': provider.provider,
                'url': f"{getenv('PUBLIC_URL')}/accounts/{new_provider}/login/",
                'name': provider.name,
                'usage_required': settings.FORCE_SOCIALACCOUNT_LOGIN
            })
        return Response(providers, status=status.HTTP_200_OK)
    

class DisablePasswordAuthenticationView(APIView):
    """
    Disable password authentication for a user. This is used when a user signs up with a social provider.
    """

# Allows the user to set the disable_password field to True if they have a social account linked
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: openapi.Response('Password authentication disabled'),
            400: 'Bad Request'
        },
        operation_description="Disable password authentication."
    )
    def post(self, request):
        user = request.user
        if SocialAccount.objects.filter(user=user).exists():
            user.disable_password = True
            user.save()
            return Response({"detail": "Password authentication disabled."}, status=status.HTTP_200_OK)
        return Response({"detail": "No social account linked."}, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        user = request.user
        user.disable_password = False
        user.save()
        return Response({"detail": "Password authentication enabled."}, status=status.HTTP_200_OK)


class APIKeyListCreateView(APIView):
    """
    List the current user's API keys or create a new one.

    GET  /auth/api-keys/   → list of keys (name, prefix, created_at, last_used_at)
    POST /auth/api-keys/   → create a new key; returns the raw token **once**
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={200: APIKeySerializer(many=True)},
        operation_description="List all API keys for the authenticated user.",
    )
    def get(self, request):
        keys = APIKey.objects.filter(user=request.user)
        serializer = APIKeySerializer(keys, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=APIKeyCreateSerializer,
        responses={
            201: openapi.Response(
                "API key created.  The ``key`` field is returned only once.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_STRING, format="uuid"),
                        "name": openapi.Schema(type=openapi.TYPE_STRING),
                        "key_prefix": openapi.Schema(type=openapi.TYPE_STRING),
                        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                        "last_used_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time", x_nullable=True),
                        "key": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Full API key – shown once, never stored.",
                        ),
                    },
                ),
            ),
            400: "Bad request – name is required.",
        },
        operation_description="Create a new API key.  Copy the returned ``key`` immediately; it will not be shown again.",
    )
    def post(self, request):
        serializer = APIKeyCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        api_key, raw_key = APIKey.generate(
            user=request.user,
            name=serializer.validated_data["name"],
        )
        response_data = APIKeySerializer(api_key).data
        response_data["key"] = raw_key
        return Response(response_data, status=status.HTTP_201_CREATED)


class APIKeyDetailView(APIView):
    """
    DELETE /auth/api-keys/<id>/  → revoke (delete) an API key
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            204: "API key deleted.",
            404: "Not found.",
        },
        operation_description="Revoke an API key by its ID.",
    )
    def delete(self, request, pk):
        api_key = get_object_or_404(APIKey, pk=pk, user=request.user)
        api_key.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MobileQRCodeView(APIView):
    """
    POST /auth/mobile-qr/  → generate a QR code for mobile app login
    GET  /auth/mobile-qr/  → get the current mobile API key if one exists
    DELETE /auth/mobile-qr/ → delete the mobile API key if one exists
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                "Mobile API key already exists",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_STRING, format="uuid"),
                        "name": openapi.Schema(type=openapi.TYPE_STRING),
                        "key_prefix": openapi.Schema(type=openapi.TYPE_STRING),
                        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                    },
                ),
            ),
            404: "No mobile API key found",
        },
        operation_description="Get the current mobile API key if one exists.",
    )
    def get(self, request):
        # Check if user already has a mobile app API key
        mobile_key = APIKey.objects.filter(
            user=request.user,
            name__startswith="Mobile App -"
        ).first()

        if mobile_key:
            serializer = APIKeySerializer(mobile_key)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(
            {"detail": "No mobile API key found."},
            status=status.HTTP_404_NOT_FOUND
        )

    @swagger_auto_schema(
        responses={
            201: openapi.Response(
                "QR code generated successfully",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_STRING, format="uuid"),
                        "name": openapi.Schema(type=openapi.TYPE_STRING),
                        "key_prefix": openapi.Schema(type=openapi.TYPE_STRING),
                        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                        "key": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Full API key – shown once, never stored.",
                        ),
                        "qr_code": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Base64-encoded PNG QR code image",
                        ),
                    },
                ),
            ),
            400: "Mobile API key already exists",
        },
        operation_description="Generate a QR code for mobile app login. Creates an API key with name 'Mobile App - [date]'.",
    )
    def post(self, request):
        # Check if user already has a mobile app API key
        existing_key = APIKey.objects.filter(
            user=request.user,
            name__startswith="Mobile App -"
        ).first()

        if existing_key:
            return Response(
                {"detail": "Mobile API key already exists. Please delete the existing one first."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate a new API key with a name like "Mobile App - March 17, 2026"
        name = f"Mobile App - {datetime.now().strftime('%B %d, %Y')}"
        api_key, raw_key = APIKey.generate(user=request.user, name=name)

        # Create QR code data with proper structure for mobile app
        qr_data = {
            "version": 1,
            "server_url": getattr(settings, 'PUBLIC_URL', 'http://localhost:8015'),
            "api_key": raw_key,
            "code_words": ["hike", "explore"]
        }

        # Generate QR code containing the JSON data
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)

        # Create QR code image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()

        # Return API key info and QR code
        response_data = APIKeySerializer(api_key).data
        response_data["key"] = raw_key
        response_data["qr_code"] = f"data:image/png;base64,{img_str}"

        return Response(response_data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        responses={
            204: "Mobile API key deleted.",
            404: "No mobile API key found.",
        },
        operation_description="Delete the mobile API key.",
    )
    def delete(self, request):
        # Find and delete the mobile app API key
        mobile_key = APIKey.objects.filter(
            user=request.user,
            name__startswith="Mobile App -"
        ).first()

        if not mobile_key:
            return Response(
                {"detail": "No mobile API key found."},
                status=status.HTTP_404_NOT_FOUND
            )

        mobile_key.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
