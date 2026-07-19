import logging

from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from adventures.throttling import EndurainAuthThrottle
from integrations.endurain_services import (
    IntegrationError,
    MfaRequired,
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
from integrations.models import EndurainIntegration
from integrations.serializers import EndurainIntegrationSerializer

logger = logging.getLogger(__name__)


class EndurainIntegrationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def get_throttles(self):
        if getattr(self, 'action', None) in ('connect', 'mfa'):
            return [EndurainAuthThrottle()]
        return super().get_throttles()

    def _get_integration(self) -> EndurainIntegration | None:
        return EndurainIntegration.objects.filter(user=self.request.user).first()

    def _error_response(self, exc: IntegrationError):
        return Response(
            {
                'message': exc.user_message,
                'error': True,
                'code': exc.code or 'endurain.error',
            },
            status=exc.status_code or status.HTTP_400_BAD_REQUEST,
        )

    def list(self, request):
        integration = self._get_integration()
        if not integration:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(EndurainIntegrationSerializer(integration).data)

    @action(detail=False, methods=['post'], url_path='connect')
    def connect(self, request):
        if EndurainIntegration.objects.filter(user=request.user).exists():
            raise ValidationError('Endurain integration already exists. Disconnect first to reconnect.')

        server_url = request.data.get('server_url')
        username = request.data.get('username')
        password = request.data.get('password')
        if not server_url or not username or not password:
            raise ValidationError('server_url, username, and password are required.')

        try:
            normalized_url = normalize_server_url(server_url)
            tokens = login_with_password(normalized_url, username, password)
            integration = save_integration_from_tokens(request.user, normalized_url, tokens)
            return Response(
                EndurainIntegrationSerializer(integration).data,
                status=status.HTTP_201_CREATED,
            )
        except MfaRequired as exc:
            mfa_token = create_mfa_pending(request.user.id, server_url, exc.username)
            return Response(
                {
                    'mfa_required': True,
                    'mfa_token': mfa_token,
                    'username': exc.username,
                    'server_url': normalize_server_url(server_url),
                    'message': exc.user_message,
                },
                status=status.HTTP_202_ACCEPTED,
            )
        except IntegrationError as exc:
            return self._error_response(exc)

    @action(detail=False, methods=['post'], url_path='mfa')
    def mfa(self, request):
        if EndurainIntegration.objects.filter(user=request.user).exists():
            raise ValidationError('Endurain integration already exists. Disconnect first to reconnect.')

        mfa_token = request.data.get('mfa_token')
        mfa_code = request.data.get('mfa_code')
        if not mfa_token or not mfa_code:
            raise ValidationError('mfa_token and mfa_code are required.')

        try:
            pending = consume_mfa_pending(request.user.id, mfa_token)
            tokens = verify_mfa(pending['server_url'], pending['username'], mfa_code)
            integration = save_integration_from_tokens(
                request.user,
                pending['server_url'],
                tokens,
            )
            return Response(
                EndurainIntegrationSerializer(integration).data,
                status=status.HTTP_201_CREATED,
            )
        except IntegrationError as exc:
            return self._error_response(exc)

    @action(detail=False, methods=['post'], url_path='disable')
    def disable(self, request):
        integration = self._get_integration()
        if not integration:
            return Response(
                {
                    'message': 'Endurain integration is not enabled for this user.',
                    'error': True,
                    'code': 'endurain.not_enabled',
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        integration.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='activities')
    def activities(self, request):
        integration = self._get_integration()
        if not integration:
            return Response(
                {
                    'message': 'You need to connect Endurain first.',
                    'error': True,
                    'code': 'endurain.not_authorized',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        try:
            page = max(1, int(request.query_params.get('page', 1)))
            per_page = min(max(1, int(request.query_params.get('per_page', 50))), 200)
        except (TypeError, ValueError):
            raise ValidationError('page and per_page must be integers.')

        try:
            raw_activities = fetch_user_activities(
                integration,
                start_date=start_date,
                end_date=end_date,
                page_number=page,
                num_records=per_page,
            )
            essential = [
                normalize_activity(activity, integration.server_url)
                for activity in raw_activities
            ]
            return Response(
                {
                    'activities': essential,
                    'count': len(essential),
                    'page': page,
                    'per_page': per_page,
                },
                status=status.HTTP_200_OK,
            )
        except IntegrationError as exc:
            return self._error_response(exc)

    @action(detail=False, methods=['get'], url_path=r'activities/(?P<activity_id>[^/.]+)')
    def activity_detail(self, request, activity_id=None):
        integration = self._get_integration()
        if not integration:
            return Response(
                {
                    'message': 'You need to connect Endurain first.',
                    'error': True,
                    'code': 'endurain.not_authorized',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            activity = fetch_activity_by_id(integration, int(activity_id))
            return Response(
                normalize_activity(activity, integration.server_url),
                status=status.HTTP_200_OK,
            )
        except IntegrationError as exc:
            return self._error_response(exc)
        except (TypeError, ValueError):
            return Response(
                {
                    'message': 'Invalid activity ID.',
                    'error': True,
                    'code': 'endurain.activity_id_required',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=['get'], url_path=r'activities/(?P<activity_id>[^/.]+)/gpx')
    def activity_gpx(self, request, activity_id=None):
        integration = self._get_integration()
        if not integration:
            return Response(
                {
                    'message': 'You need to connect Endurain first.',
                    'error': True,
                    'code': 'endurain.not_authorized',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            gpx_bytes = export_activity_gpx(integration, int(activity_id))
            activity = fetch_activity_by_id(integration, int(activity_id))
            filename = safe_gpx_filename(activity.get('name'))
            response = HttpResponse(gpx_bytes, content_type='application/gpx+xml')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except IntegrationError as exc:
            return self._error_response(exc)
        except (TypeError, ValueError):
            return Response(
                {
                    'message': 'Invalid activity ID.',
                    'error': True,
                    'code': 'endurain.activity_id_required',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
