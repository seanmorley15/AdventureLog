from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import ChangeEmailSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .serializers import CustomUserDetailsSerializer as PublicUserSerializer

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
    def get(self, request, user_id):
        user = get_object_or_404(User, uuid=user_id, public_profile=True)
        # remove the email address from the response
        user.email = None
        serializer = PublicUserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

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