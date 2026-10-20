"""The signed-in user's own account: details, media use, password sign-in, and deletion."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from users.serializers import DeleteAccountSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from users.serializers import CustomUserDetailsSerializer as PublicUserSerializer
from allauth.socialaccount.models import SocialAccount
from adventures.services.media_quota import enforce_media_storage_limit, get_media_storage_limit_bytes, get_uploaded_file_size, get_user_media_usage
from django.contrib.auth import logout
from users.services.account_deletion import AccountDeletionError, delete_user_account


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


class UserMediaUsageView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: openapi.Response('User media usage')
        },
        operation_description="Get media storage usage for the authenticated user."
    )
    def get(self, request):
        usage = get_user_media_usage(request.user)
        usage["limit_bytes"] = get_media_storage_limit_bytes()
        return Response(usage, status=status.HTTP_200_OK)


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
        profile_pic = request.FILES.get('profile_pic')
        if profile_pic:
            exclude_names = []
            if user.profile_pic and user.profile_pic.name:
                exclude_names.append(user.profile_pic.name)
            allowed, details = enforce_media_storage_limit(
                user,
                get_uploaded_file_size(profile_pic),
                exclude_names=exclude_names,
            )
            if not allowed:
                return Response(
                    {
                        "error": "Media storage limit exceeded",
                        **details,
                    },
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )
        serializer = PublicUserSerializer(user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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


class DeleteAccountView(APIView):
    """
    POST /auth/delete-account/

    Permanently delete the authenticated user's account and all associated data.
    Cancels any active Stripe subscription in cloud mode before removing the user.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=DeleteAccountSerializer,
        responses={
            204: "Account deleted.",
            400: "Invalid confirmation or password.",
            403: "Staff accounts cannot be self-deleted.",
            502: "Stripe billing cleanup failed.",
        },
        operation_description="Permanently delete the authenticated user's account.",
    )
    def post(self, request):
        user = request.user

        if user.is_staff or user.is_superuser:
            return Response(
                {"detail": "Staff accounts cannot be deleted via self-service."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = DeleteAccountSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            delete_user_account(user)
        except AccountDeletionError:
            return Response(
                {
                    "detail": (
                        "Unable to delete your account because billing cleanup failed. "
                        "Please try again or contact support."
                    )
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
