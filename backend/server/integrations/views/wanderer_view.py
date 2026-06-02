from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound

from integrations.models import WandererIntegration
from integrations.serializers import WandererIntegrationSerializer
from integrations.wanderer_services import (
    IntegrationError,
    TRAIL_EXPAND_AUTHOR,
    TRAILS_LIST_PATHS,
    make_wanderer_request,
    validate_wanderer_connection,
)


class WandererIntegrationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = WandererIntegrationSerializer

    def _get_obj(self):
        return WandererIntegration.objects.filter(user=self.request.user).first()

    def list(self, request):
        inst = self._get_obj()
        if not inst:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = self.serializer_class(inst)
        return Response(serializer.data)

    def create(self, request):
        if WandererIntegration.objects.filter(user=request.user).exists():
            raise ValidationError('Wanderer integration already exists. Use UPDATE instead.')

        server_url = request.data.get('server_url')
        api_key = request.data.get('api_key')
        if not server_url or not api_key:
            raise ValidationError('Must provide server_url and api_key in request data.')

        try:
            normalized_url = validate_wanderer_connection(server_url, api_key)
        except IntegrationError as exc:
            raise ValidationError({'error': str(exc)})

        inst = WandererIntegration.objects.create(
            user=request.user,
            server_url=normalized_url,
            api_key=api_key.strip(),
        )
        return Response(
            self.serializer_class(inst).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, pk=None):
        inst = self._get_obj()
        if not inst:
            raise NotFound('Wanderer integration not found.')
        if pk and str(inst.id) != str(pk):
            raise NotFound('Wanderer integration not found.')

        server_url = request.data.get('server_url', inst.server_url)
        api_key = (request.data.get('api_key') or '').strip() or inst.api_key

        if not server_url:
            raise ValidationError('server_url is required.')

        try:
            normalized_url = validate_wanderer_connection(server_url, api_key)
        except IntegrationError as exc:
            raise ValidationError({'error': str(exc)})

        inst.server_url = normalized_url
        inst.api_key = api_key.strip()
        inst.save(update_fields=['server_url', 'api_key'])

        return Response(self.serializer_class(inst).data)

    @action(detail=False, methods=['post'])
    def disable(self, request):
        inst = self._get_obj()
        if not inst:
            raise NotFound('Wanderer integration not found.')
        inst.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='trails')
    def trails(self, request):
        inst = self._get_obj()
        if not inst:
            raise NotFound('Wanderer integration not found.')

        params = dict(request.query_params)
        params.setdefault('expand', TRAIL_EXPAND_AUTHOR['expand'])
        last_error = None
        for path in TRAILS_LIST_PATHS:
            try:
                response = make_wanderer_request(
                    inst,
                    path,
                    params=params,
                )
                return Response(response.json())
            except IntegrationError as exc:
                last_error = exc
                if '404' in str(exc):
                    continue
                raise ValidationError({'detail': str(exc)})

        raise ValidationError({'detail': str(last_error)})
