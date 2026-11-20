import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.exceptions import APIError
from integrations.errors import IntegrationError
from integrations.models import WandererIntegration
from integrations.serializers import WandererIntegrationSerializer
from integrations.services.wanderer import (
    TRAIL_EXPAND_AUTHOR,
    TRAILS_LIST_PATHS,
    make_wanderer_request,
    validate_wanderer_connection,
)

logger = logging.getLogger(__name__)

_NOT_CONNECTED = OpenApiResponse(description='You have not connected Wanderer (`wanderer.not_connected`).')
_CHECK_FAILED = OpenApiResponse(description='The server could not be reached with these details '
                                '(`wanderer.connection_failed`).')


class WandererViewSet(viewsets.GenericViewSet):
    """
    Your connection to a Wanderer trail server, for attaching its trails to places and days.
    Routed as a singleton. The API key is never returned.
    """

    openapi_tags = ['Integrations']
    queryset = WandererIntegration.objects.none()
    serializer_class = WandererIntegrationSerializer

    def get_integration(self):
        integration = WandererIntegration.objects.filter(user=self.request.user).first()
        if integration is None:
            raise APIError('Connect Wanderer first.', code='wanderer.not_connected', status=status.HTTP_404_NOT_FOUND)
        return integration

    @staticmethod
    def _checked_url(server_url, api_key):
        try:
            return validate_wanderer_connection(server_url, api_key)
        except IntegrationError as exc:
            logger.warning('Wanderer connection check failed: %s', exc.user_message)
            raise APIError(exc.user_message, code='wanderer.connection_failed')

    @extend_schema(responses={200: WandererIntegrationSerializer, 404: _NOT_CONNECTED})
    def retrieve(self, request):
        """Get your Wanderer connection"""
        return Response(self.get_serializer(self.get_integration()).data)

    @extend_schema(
        request=WandererIntegrationSerializer,
        responses={201: WandererIntegrationSerializer, 400: _CHECK_FAILED,
                   409: OpenApiResponse(description='Already connected. Use PATCH.')},
    )
    def create(self, request):
        """
        Connect Wanderer

        Checks the address and API key against the server before saving.
        """
        if WandererIntegration.objects.filter(user=request.user).exists():
            raise APIError('Wanderer is already connected. Change it instead.', code='conflict', status=409)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        api_key = (serializer.validated_data.get('api_key') or '').strip()
        if not api_key:
            raise serializers.ValidationError({'api_key': ['This field is required.']})
        server_url = self._checked_url(serializer.validated_data['server_url'], api_key)
        integration = WandererIntegration.objects.create(user=request.user, server_url=server_url, api_key=api_key)
        return Response(self.get_serializer(integration).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=WandererIntegrationSerializer,
        responses={200: WandererIntegrationSerializer, 400: _CHECK_FAILED, 404: _NOT_CONNECTED},
    )
    def partial_update(self, request):
        """
        Change your Wanderer connection

        Send what changes; leave out `api_key` to keep the current one. Checked again before
        saving.
        """
        integration = self.get_integration()
        serializer = self.get_serializer(integration, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        api_key = (serializer.validated_data.get('api_key') or '').strip() or integration.api_key
        integration.server_url = self._checked_url(
            serializer.validated_data.get('server_url', integration.server_url), api_key
        )
        integration.api_key = api_key
        integration.save(update_fields=['server_url', 'api_key'])
        return Response(self.get_serializer(integration).data)

    @extend_schema(responses={204: OpenApiResponse(description='Disconnected.'), 404: _NOT_CONNECTED})
    def destroy(self, request):
        """Disconnect Wanderer"""
        self.get_integration().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        responses={
            200: OpenApiResponse({'type': 'object'}, description="Wanderer's trail list, as Wanderer returns it "
                                 '(`items`, `page`, `totalItems`, ...).'),
            404: _NOT_CONNECTED,
            502: OpenApiResponse(description='Wanderer failed (`upstream_error`).'),
        },
    )
    @action(detail=False, methods=['get'], url_path='trails')
    def trails(self, request):
        """
        List Wanderer trails

        Query parameters (`filter`, `sort`, `page`, `perPage`, ...) are passed to Wanderer's
        trail list as they are; the trail author is included.
        """
        integration = self.get_integration()
        params = dict(request.query_params)
        params.pop('format', None)
        params.setdefault('expand', TRAIL_EXPAND_AUTHOR['expand'])
        for path in TRAILS_LIST_PATHS:
            try:
                return Response(make_wanderer_request(integration, path, params=params).json())
            except IntegrationError as exc:
                if exc.status_code == 404:
                    continue
                logger.warning('Wanderer trails request failed: %s', exc.user_message)
                break
        raise APIError('Trails could not be loaded from Wanderer.', code='upstream_error', status=502)
