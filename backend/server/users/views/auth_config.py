"""What the sign-in and sign-up screens need to know before anyone is signed in."""

from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.middleware.csrf import get_token
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.public_url import get_public_url
from users.serializers import AuthConfigSerializer, CsrfTokenSerializer


def _social_providers():
    providers = []
    for app in SocialApp.objects.filter(sites=settings.SITE_ID):
        path = f'oidc/{app.provider_id}' if app.provider == 'openid_connect' else app.provider
        providers.append({
            'provider': app.provider,
            'name': app.name,
            'url': f'{get_public_url()}/accounts/{path}/login/',
            'usage_required': settings.FORCE_SOCIALACCOUNT_LOGIN,
        })
    return providers


class AuthConfigView(APIView):
    openapi_tags = ['Authentication']
    permission_classes = [AllowAny]
    # Requested by every sign-in and sign-up page. A 429 here would lock people out.
    throttle_classes = []

    @extend_schema(
        responses=AuthConfigSerializer,
        examples=[
            OpenApiExample(
                'Open registration with GitHub',
                value={
                    'registration': {'enabled': True, 'message': ''},
                    'password_policy': {'min_length': 8, 'validators_enabled': True},
                    'legal_links': {'terms_of_service_url': None, 'privacy_policy_url': None},
                    'social_providers': [{
                        'provider': 'github',
                        'name': 'GitHub',
                        'url': 'https://adventurelog.example.com/accounts/github/login/',
                        'usage_required': False,
                    }],
                },
            )
        ],
    )
    def get(self, request):
        """
        Get the sign-in configuration

        Whether sign-up is open, the password rules, optional terms and privacy links to show on
        sign-up, and the social providers people can sign in with.
        """
        return Response({
            'registration': {
                'enabled': not settings.DISABLE_REGISTRATION,
                'message': settings.DISABLE_REGISTRATION_MESSAGE,
            },
            'password_policy': {
                'min_length': settings.ACCOUNT_PASSWORD_MIN_LENGTH,
                'validators_enabled': settings.AUTH_PASSWORD_VALIDATORS_ENABLED,
            },
            'legal_links': {
                'terms_of_service_url': settings.TERMS_OF_SERVICE_URL or None,
                'privacy_policy_url': settings.PRIVACY_POLICY_URL or None,
            },
            'social_providers': _social_providers(),
        })


class CsrfTokenView(APIView):
    openapi_tags = ['Authentication']
    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(responses=CsrfTokenSerializer)
    def get(self, request):
        """
        Get a CSRF token

        Only needed with session (cookie) authentication: send the token as `X-CSRFToken` on
        every request that changes data. Also sets the `csrftoken` cookie. API-key requests do
        not need it.
        """
        return Response({'csrf_token': get_token(request)})
