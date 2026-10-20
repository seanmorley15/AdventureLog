"""What the sign-in and sign-up screens need to know before anyone is signed in."""

from os import getenv
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.conf import settings
from allauth.socialaccount.models import SocialApp


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


class PasswordPolicyView(APIView):
    # Used by auth pages to validate passwords client-side before submission.
    throttle_classes = []

    @swagger_auto_schema(
        responses={
            200: openapi.Response('Password policy configuration'),
            400: 'Bad Request'
        },
        operation_description="Get the configured password policy for this instance."
    )
    def get(self, request):
        return Response(
            {
                "min_length": settings.ACCOUNT_PASSWORD_MIN_LENGTH,
                "validators_enabled": settings.AUTH_PASSWORD_VALIDATORS_ENABLED,
            },
            status=status.HTTP_200_OK,
        )


class SignupLegalLinksView(APIView):
    # Used by the signup page to show optional terms/privacy acceptance.
    throttle_classes = []

    @swagger_auto_schema(
        responses={
            200: openapi.Response('Signup legal link configuration'),
        },
        operation_description="Get configured Terms of Service and Privacy Policy URLs."
    )
    def get(self, request):
        return Response(
            {
                "terms_of_service_url": settings.TERMS_OF_SERVICE_URL or None,
                "privacy_policy_url": settings.PRIVACY_POLICY_URL or None,
            },
            status=status.HTTP_200_OK,
        )


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
