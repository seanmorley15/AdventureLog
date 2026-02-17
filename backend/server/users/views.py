from os import getenv
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from .serializers import ChangeEmailSerializer
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


class APITokenView(APIView):
    """
    Manage API token for MCP (Model Context Protocol) access.
    Users can view, create, regenerate, or delete their API token.
    This token is used to authenticate with the MCP endpoint for AI agent integration.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: openapi.Response('API token details'),
            404: 'No token exists'
        },
        operation_description="Get the current API token for MCP access."
    )
    def get(self, request):
        """Get the user's current API token."""
        try:
            token = Token.objects.get(user=request.user)
            return Response({
                "token": token.key,
                "created": token.created,
                "mcp_endpoint": f"{getenv('PUBLIC_URL', 'http://localhost:8000')}/api/mcp"
            }, status=status.HTTP_200_OK)
        except Token.DoesNotExist:
            return Response({
                "detail": "No API token exists. Use POST to create one.",
                "mcp_endpoint": f"{getenv('PUBLIC_URL', 'http://localhost:8000')}/api/mcp"
            }, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        responses={
            201: openapi.Response('API token created'),
            200: openapi.Response('API token regenerated')
        },
        operation_description="Create or regenerate API token for MCP access."
    )
    def post(self, request):
        """Create a new API token or regenerate existing one."""
        # Delete existing token if it exists
        Token.objects.filter(user=request.user).delete()
        # Create new token
        token = Token.objects.create(user=request.user)
        return Response({
            "token": token.key,
            "created": token.created,
            "mcp_endpoint": f"{getenv('PUBLIC_URL', 'http://localhost:8000')}/api/mcp",
            "detail": "API token created. Use this token to authenticate with the MCP endpoint."
        }, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        responses={
            200: openapi.Response('API token deleted'),
            404: 'No token to delete'
        },
        operation_description="Delete the API token, revoking MCP access."
    )
    def delete(self, request):
        """Delete the user's API token."""
        deleted_count, _ = Token.objects.filter(user=request.user).delete()
        if deleted_count > 0:
            return Response({
                "detail": "API token deleted. MCP access has been revoked."
            }, status=status.HTTP_200_OK)
        return Response({
            "detail": "No API token to delete."
        }, status=status.HTTP_404_NOT_FOUND)

