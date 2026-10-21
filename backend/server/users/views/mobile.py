"""The API key the mobile app signs in with, delivered as a QR code."""

import base64
import io
import json
from datetime import datetime

import qrcode
from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import APIError
from users.models import APIKey
from users.serializers import APIKeySerializer, MobileKeySerializer

MOBILE_KEY_PREFIX = 'Mobile App -'


def _mobile_key(user):
    return APIKey.objects.filter(user=user, name__startswith=MOBILE_KEY_PREFIX).first()


def _qr_data_uri(payload):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(json.dumps(payload))
    qr.make(fit=True)
    buffer = io.BytesIO()
    qr.make_image(fill_color='black', back_color='white').save(buffer, format='PNG')
    return f'data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}'


class MobileKeyView(APIView):
    """
    The mobile app's API key. It is an ordinary API key named ``Mobile App - <date>``, so it is
    also listed (and can be revoked) with the other keys.
    """

    openapi_tags = ['Account']

    @extend_schema(responses={200: APIKeySerializer, 404: OpenApiResponse(description='No mobile key exists.')})
    def get(self, request):
        """Get the mobile app key"""
        key = _mobile_key(request.user)
        if key is None:
            raise APIError('No mobile API key exists.', code='not_found', status=status.HTTP_404_NOT_FOUND)
        return Response(APIKeySerializer(key).data)

    @extend_schema(
        request=None,
        responses={
            201: MobileKeySerializer,
            409: OpenApiResponse(description='A mobile key already exists. Delete it first.'),
        },
    )
    def post(self, request):
        """
        Create the mobile app key

        Creates the key and a QR code for the AdventureLog app to scan. The QR code holds JSON:
        `{"version": 1, "server_url", "api_key", "code_words"}`. Like any key, it is shown only
        in this response.
        """
        if _mobile_key(request.user) is not None:
            raise APIError(
                'A mobile API key already exists. Delete it first.',
                code='conflict',
                status=status.HTTP_409_CONFLICT,
            )
        name = f"{MOBILE_KEY_PREFIX} {datetime.now().strftime('%B %d, %Y')}"
        api_key, raw_key = APIKey.generate(user=request.user, name=name)
        data = APIKeySerializer(api_key).data
        data['key'] = raw_key
        data['qr_code'] = _qr_data_uri({
            'version': 1,
            'server_url': settings.PUBLIC_URL,
            'api_key': raw_key,
            'code_words': ['hike', 'explore'],
        })
        return Response(data, status=status.HTTP_201_CREATED)

    @extend_schema(responses={204: OpenApiResponse(description='The mobile key was revoked.')})
    def delete(self, request):
        """Revoke the mobile app key"""
        key = _mobile_key(request.user)
        if key is None:
            raise APIError('No mobile API key exists.', code='not_found', status=status.HTTP_404_NOT_FOUND)
        key.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
