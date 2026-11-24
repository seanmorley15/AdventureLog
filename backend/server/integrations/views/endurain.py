import logging

from django.http import HttpResponse
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.exceptions import APIError
from core.serializers import validated
from integrations.errors import MfaRequired
from integrations.models import EndurainIntegration
from integrations.serializers import EndurainIntegrationSerializer
from integrations.services.endurain import (
    consume_mfa_pending,
    create_mfa_pending,
    export_activity_gpx,
    fetch_activity_by_id,
    fetch_user_activities,
    login_with_password,
    normalize_activity,
    normalize_server_url,
    safe_gpx_filename,
    save_integration_from_tokens,
    verify_mfa,
)
from integrations.throttling import EndurainAuthThrottle

logger = logging.getLogger(__name__)


class EndurainConnectSerializer(serializers.Serializer):
    server_url = serializers.CharField(help_text='Your Endurain address.')
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, help_text='Used once to get tokens; never stored.')


class EndurainMfaSerializer(serializers.Serializer):
    mfa_token = serializers.CharField(help_text='From the 202 answer of `connect/`.')
    mfa_code = serializers.CharField(help_text='The code from your authenticator app.')


class EndurainActivitiesQuerySerializer(serializers.Serializer):
    start_date = serializers.CharField(required=False, help_text='ISO 8601 date; activities from this day.')
    end_date = serializers.CharField(required=False, help_text='ISO 8601 date; activities until this day.')
    page = serializers.IntegerField(default=1, min_value=1)
    per_page = serializers.IntegerField(default=50, min_value=1, max_value=200)


ENDURAIN_ACTIVITY = {
    'type': 'object',
    'description': 'An activity normalized from Endurain, in the same units as Strava activities, with `export_gpx`.',
}
ACTIVITY_ID = OpenApiParameter('activity_id', int, OpenApiParameter.PATH, description='The Endurain activity id.')
_NOT_CONNECTED = OpenApiResponse(description='You have not connected Endurain (`endurain.not_authorized`).')
_UPSTREAM = OpenApiResponse(description='Endurain answered with an error (`endurain.fetch_failed`, '
                            '`endurain.reconnect_required`).')


class EndurainViewSet(viewsets.GenericViewSet):
    """
    Your connection to an Endurain fitness server, for importing activities. Routed as a
    singleton. AdventureLog keeps Endurain's tokens, never your password.
    """

    openapi_tags = ['Integrations']
    queryset = EndurainIntegration.objects.none()
    serializer_class = EndurainIntegrationSerializer

    def get_throttles(self):
        if getattr(self, 'action', None) in ('connect', 'mfa'):
            return [EndurainAuthThrottle()]
        return super().get_throttles()

    def get_integration(self):
        integration = EndurainIntegration.objects.filter(user=self.request.user).first()
        if integration is None:
            raise APIError(
                'Connect Endurain first.', code='endurain.not_authorized', status=status.HTTP_404_NOT_FOUND
            )
        return integration

    def _ensure_not_connected(self):
        if EndurainIntegration.objects.filter(user=self.request.user).exists():
            raise APIError(
                'Endurain is already connected. Disconnect first to reconnect.',
                code='endurain.integration_exists', status=status.HTTP_409_CONFLICT,
            )

    @extend_schema(responses={200: EndurainIntegrationSerializer, 404: _NOT_CONNECTED})
    def retrieve(self, request):
        """Get your Endurain connection"""
        return Response(EndurainIntegrationSerializer(self.get_integration()).data)

    @extend_schema(responses={204: OpenApiResponse(description='Disconnected.'), 404: _NOT_CONNECTED})
    def destroy(self, request):
        """Disconnect Endurain"""
        self.get_integration().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request=EndurainConnectSerializer,
        responses={
            201: EndurainIntegrationSerializer,
            202: OpenApiResponse(inline_serializer('EndurainMfaRequired', fields={
                'mfa_required': serializers.BooleanField(),
                'mfa_token': serializers.CharField(help_text='Send with the code to `mfa/`.'),
                'username': serializers.CharField(),
                'server_url': serializers.CharField(),
                'message': serializers.CharField(),
            }), description='The account uses two-factor sign-in: finish with `mfa/`.'),
            400: OpenApiResponse(description='Wrong details or unreachable server (`endurain.invalid_credentials`, '
                                 '`endurain.connection_failed`, `endurain.invalid_server_url`).'),
            409: OpenApiResponse(description='Already connected (`endurain.integration_exists`).'),
            429: OpenApiResponse(description='Too many attempts. This limit is always on.'),
        },
    )
    @action(detail=False, methods=['post'], url_path='connect')
    def connect(self, request):
        """
        Connect Endurain

        Signs in to your Endurain server with your username and password and keeps the tokens
        it returns. When the account uses two-factor sign-in, answers 202 and you finish with
        `mfa/`.
        """
        self._ensure_not_connected()
        params = validated(EndurainConnectSerializer, request.data)
        normalized_url = normalize_server_url(params['server_url'])
        try:
            tokens = login_with_password(normalized_url, params['username'], params['password'])
        except MfaRequired as exc:
            return Response(
                {
                    'mfa_required': True,
                    'mfa_token': create_mfa_pending(request.user.id, params['server_url'], exc.username),
                    'username': exc.username,
                    'server_url': normalized_url,
                    'message': exc.user_message,
                },
                status=status.HTTP_202_ACCEPTED,
            )
        integration = save_integration_from_tokens(request.user, normalized_url, tokens)
        return Response(EndurainIntegrationSerializer(integration).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=EndurainMfaSerializer,
        responses={
            201: EndurainIntegrationSerializer,
            400: OpenApiResponse(description='Wrong or expired code (`endurain.mfa_failed`).'),
            409: OpenApiResponse(description='Already connected (`endurain.integration_exists`).'),
        },
    )
    @action(detail=False, methods=['post'], url_path='mfa')
    def mfa(self, request):
        """
        Finish connecting with a two-factor code

        Completes a `connect/` that answered 202.
        """
        self._ensure_not_connected()
        params = validated(EndurainMfaSerializer, request.data)
        pending = consume_mfa_pending(request.user.id, params['mfa_token'])
        tokens = verify_mfa(pending['server_url'], pending['username'], params['mfa_code'])
        integration = save_integration_from_tokens(request.user, pending['server_url'], tokens)
        return Response(EndurainIntegrationSerializer(integration).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        parameters=[EndurainActivitiesQuerySerializer],
        responses={
            200: inline_serializer('EndurainActivityList', fields={
                'activities': serializers.ListField(child=serializers.DictField()),
                'count': serializers.IntegerField(help_text='Activities on this page.'),
                'page': serializers.IntegerField(),
                'per_page': serializers.IntegerField(),
            }),
            404: _NOT_CONNECTED,
            502: _UPSTREAM,
        },
    )
    @action(detail=False, methods=['get'], url_path='activities')
    def activities(self, request):
        """
        List your Endurain activities

        A page at a time, optionally between two dates.
        """
        params = validated(EndurainActivitiesQuerySerializer, request.query_params)
        integration = self.get_integration()
        raw_activities = fetch_user_activities(
            integration,
            start_date=params.get('start_date'),
            end_date=params.get('end_date'),
            page_number=params['page'],
            num_records=params['per_page'],
        )
        activities = [normalize_activity(activity, integration.server_url) for activity in raw_activities]
        return Response({
            'activities': activities,
            'count': len(activities),
            'page': params['page'],
            'per_page': params['per_page'],
        })

    @extend_schema(parameters=[ACTIVITY_ID], responses={200: ENDURAIN_ACTIVITY, 404: _NOT_CONNECTED, 502: _UPSTREAM})
    @action(detail=False, methods=['get'], url_path=r'activities/(?P<activity_id>\d+)')
    def activity_detail(self, request, activity_id=None):
        """Get an Endurain activity"""
        integration = self.get_integration()
        activity = fetch_activity_by_id(integration, int(activity_id))
        return Response(normalize_activity(activity, integration.server_url))

    @extend_schema(
        parameters=[ACTIVITY_ID],
        responses={
            (200, 'application/gpx+xml'): OpenApiResponse(response=bytes, description='The GPX track.'),
            404: OpenApiResponse(description='No such activity, or it has no GPS data (`endurain.gpx_unavailable`).'),
            502: _UPSTREAM,
        },
    )
    @action(detail=False, methods=['get'], url_path=r'activities/(?P<activity_id>\d+)/gpx')
    def activity_gpx(self, request, activity_id=None):
        """
        Download an activity's GPX track

        Built from the activity's GPS stream, for attaching to an AdventureLog activity.
        """
        integration = self.get_integration()
        gpx_bytes = export_activity_gpx(integration, int(activity_id))
        activity = fetch_activity_by_id(integration, int(activity_id))
        response = HttpResponse(gpx_bytes, content_type='application/gpx+xml')
        response['Content-Disposition'] = f'attachment; filename="{safe_gpx_filename(activity.get("name"))}"'
        return response
