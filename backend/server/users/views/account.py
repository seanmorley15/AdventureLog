"""The signed-in user's own account: details, media use, password sign-in, and deletion."""

from django.contrib.auth import logout
from allauth.socialaccount.models import SocialAccount
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from adventures.models import CollectionInvite
from adventures.services.discussion import unread_comment_count
from adventures.services.media_quota import (
    ensure_media_storage_available,
    get_media_storage_limit_bytes,
    get_uploaded_file_size,
    get_user_media_usage,
)
from core.exceptions import APIError
from users.serializers import (
    AccountSerializer,
    CustomUserDetailsSerializer,
    DeleteAccountSerializer,
    MediaUsageSerializer,
    PasswordLoginSerializer,
)
from users.services.account_deletion import AccountDeletionError, delete_user_account


@extend_schema_view(
    partial_update=extend_schema(
        summary='Update your profile',
        description=(
            'Change your profile and preferences. Send JSON, or `multipart/form-data` to upload a new '
            '`profile_pic`.\n\n'
            'Turning `public_profile` off also removes you from collections other people shared with you '
            'and cancels invites you have not answered. The response then includes '
            '`left_shared_collections` and `revoked_collection_invites` with how many were affected.'
        ),
        request=CustomUserDetailsSerializer,
        responses={
            200: CustomUserDetailsSerializer,
            413: OpenApiResponse(description='The new profile picture would exceed your media storage.'),
        },
    ),
)
class AccountViewSet(viewsets.GenericViewSet):
    """
    The signed-in user's account.

    Routed with ``core.routers.SingletonRouter``: there is one account per user at
    ``/api/account/``, so no id appears in the path.
    """

    openapi_tags = ['Account']
    serializer_class = CustomUserDetailsSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    # The app loads the account on every page; a global rate limit would sign people out.
    throttle_classes = []

    def account_extras(self, user):
        """Fields added to ``GET /api/account/`` by deployments that know more (hosted billing)."""
        return {}

    @extend_schema(responses=AccountSerializer)
    def retrieve(self, request):
        """
        Get your account

        Your profile plus what the app's header shows: how many collection invites are waiting
        and how many comments you have not read. On hosted servers the subscription is included.
        """
        user = request.user
        return Response({
            'user': CustomUserDetailsSerializer(user, context={'request': request}).data,
            'pending_invite_count': CollectionInvite.objects.filter(invited_user=user).count(),
            'unread_comment_count': unread_comment_count(user),
            **self.account_extras(user),
        })

    def partial_update(self, request):
        user = request.user
        profile_pic = request.FILES.get('profile_pic')
        if profile_pic:
            exclude_names = [user.profile_pic.name] if user.profile_pic and user.profile_pic.name else []
            ensure_media_storage_available(user, get_uploaded_file_size(profile_pic), exclude_names=exclude_names)
        serializer = CustomUserDetailsSerializer(user, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        request=DeleteAccountSerializer,
        responses={
            204: OpenApiResponse(description='The account and everything it owns were deleted.'),
            403: OpenApiResponse(description='Staff accounts cannot delete themselves here.'),
            502: OpenApiResponse(description='The hosted billing provider could not be cleaned up; nothing was deleted.'),
        },
    )
    def destroy(self, request):
        """
        Delete your account

        Permanently deletes the account and everything it owns. Send your username as
        `confirmation`, and your `password` unless the account signs in only through a social
        provider. On hosted servers the subscription is cancelled first. Ends the session.
        """
        user = request.user
        if user.is_staff or user.is_superuser:
            raise APIError(
                'Staff accounts cannot be deleted here. Use the admin site.',
                code='permission_denied',
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = DeleteAccountSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        try:
            delete_user_account(user)
        except AccountDeletionError as exc:
            raise APIError(
                'Unable to delete your account because billing cleanup failed. '
                'Please try again or contact support.',
                code='billing_cleanup_failed',
                status=status.HTTP_502_BAD_GATEWAY,
            ) from exc
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses=MediaUsageSerializer)
    @action(detail=False, methods=['get'], url_path='media-usage')
    def media_usage(self, request):
        """
        Get your media storage use

        Bytes and file counts for images, attachments and profile pictures, and the storage
        limit (`null` when the server sets none).
        """
        usage = get_user_media_usage(request.user)
        usage['limit_bytes'] = get_media_storage_limit_bytes()
        return Response(usage)

    @extend_schema(request=None, responses=PasswordLoginSerializer)
    @action(detail=False, methods=['post'], url_path='password-login/disable')
    def disable_password_login(self, request):
        """
        Turn off password sign-in

        Only for accounts with a linked social provider, which then becomes the only way to sign
        in. Answers `400 no_social_account` otherwise.
        """
        user = request.user
        if not SocialAccount.objects.filter(user=user).exists():
            raise APIError('Link a social account before turning off password sign-in.', code='no_social_account')
        user.disable_password = True
        user.save(update_fields=['disable_password'])
        return Response({'disable_password': True})

    @extend_schema(request=None, responses=PasswordLoginSerializer)
    @action(detail=False, methods=['post'], url_path='password-login/enable')
    def enable_password_login(self, request):
        """Turn password sign-in back on"""
        user = request.user
        user.disable_password = False
        user.save(update_fields=['disable_password'])
        return Response({'disable_password': False})
