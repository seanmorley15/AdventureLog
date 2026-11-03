from datetime import timedelta

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from integrations.serializers import ImmichAssetSerializer, ImmichIntegrationSerializer, ImmichSearchQuerySerializer
from core.net import self_hosted_session
from integrations.errors import IntegrationError
from integrations.services import server_urls
from integrations.models import ImmichIntegration
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
import requests
from adventures.models import ContentImage
from adventures.access.audience import has_guest_token
from adventures.access.file_permissions import can_read_content_image
from adventures.throttling import ImageProxyThrottle
from django.http import HttpResponse
from core.exceptions import APIError
from core.pagination import StandardResultsSetPagination
from core.parsing import as_uuid
from core.public_url import get_public_url
from core.serializers import validated
import logging

logger = logging.getLogger(__name__)

IMMICH_SEARCH_SIZE = 1000
IMMICH_SEARCH_VISIBILITY = 'timeline'
# Seconds to wait on the user's Immich server for list/search calls; large libraries can be slow.
IMMICH_REQUEST_TIMEOUT = 30

def immich_get(url, **kwargs):
    """GET from an Immich server the user configured. Never dials a metadata or link-local address."""
    with self_hosted_session() as session:
        return session.get(url, **kwargs)


def immich_post(url, **kwargs):
    with self_hosted_session() as session:
        return session.post(url, **kwargs)


def _server_down():
    return APIError('The Immich server is down or unreachable.', code='immich.server_down', status=503)


def _no_items(code='immich.no_items_found'):
    return APIError('No items found.', code=code, status=status.HTTP_404_NOT_FOUND)


_ASSET_PAGE = inline_serializer('PaginatedImmichAssetList', fields={
    'count': serializers.IntegerField(),
    'next': serializers.URLField(allow_null=True),
    'previous': serializers.URLField(allow_null=True),
    'results': ImmichAssetSerializer(many=True),
})


def _paginated_assets():
    return OpenApiResponse(_ASSET_PAGE, description='A page of assets (`?page=`, `?page_size=`).')


_NOT_CONNECTED = OpenApiResponse(description='You have not connected Immich (`immich.integration_missing`).')
_DOWN = OpenApiResponse(description='Your Immich server is unreachable (`immich.server_down`).')


class ImmichViewSet(viewsets.GenericViewSet):
    """
    Your connection to an Immich photo server, and browsing it.

    Routed as a singleton: there is one connection per user, at `/api/integrations/immich/`.
    """

    openapi_tags = ['Integrations']
    serializer_class = ImmichIntegrationSerializer
    queryset = ImmichIntegration.objects.all()
    pagination_class = StandardResultsSetPagination
    # Actions that page their results set this (see core.openapi.AutoSchema._get_paginator).
    paginate_action = False

    def get_integration(self):
        integration = ImmichIntegration.objects.filter(user=self.request.user).first()
        if integration is None:
            raise APIError(
                'Connect an Immich server first.', code='immich.integration_missing', status=status.HTTP_404_NOT_FOUND
            )
        return integration

    # -- The connection ------------------------------------------------------------------

    @extend_schema(responses={200: ImmichIntegrationSerializer, 404: _NOT_CONNECTED})
    def retrieve(self, request):
        """Get your Immich connection"""
        return Response(self.get_serializer(self.get_integration()).data)

    @extend_schema(
        request=ImmichIntegrationSerializer,
        responses={
            201: ImmichIntegrationSerializer,
            400: OpenApiResponse(description='The server could not be reached with these details '
                                 '(`immich.connection_failed`, with `details`).'),
            409: OpenApiResponse(description='Already connected (`immich.integration_exists`). Use PATCH.'),
        },
    )
    def create(self, request):
        """
        Connect Immich

        Checks the address and API key against the server before saving. The key is never
        returned.
        """
        if ImmichIntegration.objects.filter(user=request.user).exists():
            raise APIError(
                'You already have an Immich connection. Change it instead.',
                code='immich.integration_exists', status=status.HTTP_409_CONFLICT,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        server_url = self._checked_server_url(
            serializer.validated_data.get('server_url'), serializer.validated_data.get('api_key')
        )
        serializer.save(user=request.user, server_url=server_url)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=ImmichIntegrationSerializer,
        responses={200: ImmichIntegrationSerializer, 404: _NOT_CONNECTED,
                   400: OpenApiResponse(description='`immich.connection_failed`.')},
    )
    def partial_update(self, request):
        """
        Change your Immich connection

        Send what changes; the connection is checked again before saving.
        """
        integration = self.get_integration()
        serializer = self.get_serializer(integration, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        server_url = self._checked_server_url(
            serializer.validated_data.get('server_url', integration.server_url),
            serializer.validated_data.get('api_key', integration.api_key),
        )
        serializer.save(server_url=server_url)
        return Response(serializer.data)

    @extend_schema(responses={204: OpenApiResponse(description='Disconnected.'), 404: _NOT_CONNECTED})
    def destroy(self, request):
        """
        Disconnect Immich

        Photos already copied into AdventureLog stay; linked ones stop loading.
        """
        self.get_integration().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _checked_server_url(self, server_url, api_key):
        is_valid, corrected_server_url, error_message = self._validate_immich_connection(server_url, api_key)
        if not is_valid:
            raise APIError(
                f'Cannot connect to Immich server: {error_message}',
                code='immich.connection_failed', details=error_message,
            )
        return corrected_server_url

    def _validate_immich_connection(self, server_url, api_key):
        """
        Validate connection to Immich server before saving integration.
        Returns tuple: (is_valid, corrected_server_url, error_message)
        """
        if not server_url or not api_key:
            return False, server_url, "Server URL and API key are required"
        
        # Ensure server_url has proper format
        if not server_url.startswith(('http://', 'https://')):
            server_url = f"https://{server_url}"
        
        # Reject addresses that must never be called (credentials, cloud metadata) before trying them.
        try:
            original_server_url = server_urls.normalize_server_url(server_url, 'Immich', IntegrationError)
        except IntegrationError as exc:
            return False, server_url.rstrip('/'), exc.user_message
        
        # Try both with and without /api prefix
        test_configs = [
            (original_server_url, f"{original_server_url}/users/me"),
            (f"{original_server_url}/api", f"{original_server_url}/api/users/me")
        ]
        
        headers = {
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        }
        
        for corrected_url, test_endpoint in test_configs:
            try:
                response = immich_get(
                    test_endpoint, 
                    headers=headers, 
                    timeout=10,  # 10 second timeout
                    verify=True  # SSL verification
                )
                
                if response.status_code == 200:
                    try:
                        json_response = response.json()
                        # Validate expected Immich user response structure
                        required_fields = ['id', 'email', 'name', 'isAdmin', 'createdAt']
                        if all(field in json_response for field in required_fields):
                            return True, corrected_url, None
                        else:
                            continue  # Try next endpoint
                    except (ValueError, KeyError):
                        continue  # Try next endpoint
                elif response.status_code == 401:
                    return False, original_server_url, "Invalid API key or unauthorized access"
                elif response.status_code == 403:
                    return False, original_server_url, "Access forbidden - check API key permissions"
                # Continue to next endpoint for 404 errors
                    
            except requests.exceptions.ConnectTimeout:
                return False, original_server_url, "Connection timeout - server may be unreachable"
            except requests.exceptions.ConnectionError:
                return False, original_server_url, "Cannot connect to server - check URL and network connectivity"
            except requests.exceptions.SSLError:
                return False, original_server_url, "SSL certificate error - check server certificate"
            except requests.exceptions.RequestException as e:
                logger.error(f"RequestException during Immich connection validation: {str(e)}")
                return False, original_server_url, "Connection failed due to a network error."
            except Exception as e:
                logger.error(f"Unexpected error during Immich connection validation: {str(e)}")
                return False, original_server_url, "An unexpected error occurred while validating the connection."
        
        # If we get here, none of the endpoints worked
        return False, original_server_url, "Immich server endpoint not found - check server URL"

    # -- Browsing ------------------------------------------------------------------------

    def _build_date_range_arguments(self, selected_date):
        next_day = selected_date + timedelta(days=1)
        return {
            'takenAfter': f'{selected_date.strftime("%Y-%m-%d")}T00:00:00.000Z',
            'takenBefore': f'{next_day.strftime("%Y-%m-%d")}T00:00:00.000Z',
        }

    def _paginate_immich_assets(self, integration, request, items):
        public_url = get_public_url()
        for item in items:
            item['image_url'] = f'{public_url}/api/integrations/immich/assets/{integration.id}/{item["id"]}/'

        paginator = self.pagination_class()
        result_page = paginator.paginate_queryset(items, request)
        return paginator.get_paginated_response(result_page)

    def _fetch_immich_search_assets(
        self,
        integration,
        request,
        arguments,
        search_type='metadata',
        not_found_code='immich.no_items_found',
    ):
        url = f'{integration.server_url}/search/{search_type}'
        items = []
        page = 1

        while True:
            try:
                immich_fetch = immich_post(
                    url,
                    headers={'x-api-key': integration.api_key},
                    json={
                        'size': IMMICH_SEARCH_SIZE,
                        'page': page,
                        'visibility': IMMICH_SEARCH_VISIBILITY,
                        **arguments,
                    },
                    timeout=IMMICH_REQUEST_TIMEOUT,
                )
                res = immich_fetch.json()
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                raise _server_down()

            if not immich_fetch.ok:
                logger.warning(
                    'Immich search request failed: status=%s response=%s',
                    immich_fetch.status_code,
                    res,
                )
                raise _no_items(not_found_code)

            assets = res.get('assets')
            if not isinstance(assets, dict):
                break

            page_items = assets.get('items') or []
            if page_items:
                items.extend(page_items)

            next_page = assets.get('nextPage')
            if next_page:
                try:
                    page = int(next_page)
                    continue
                except (TypeError, ValueError):
                    logger.warning(
                        'Immich search returned invalid nextPage value: %s',
                        next_page,
                    )

            if len(page_items) < IMMICH_SEARCH_SIZE:
                break

            page += 1

        if items:
            return self._paginate_immich_assets(integration, request, items)

        raise _no_items(not_found_code)

    @extend_schema(
        parameters=[ImmichSearchQuerySerializer],
        responses={200: _paginated_assets(), 404: OpenApiResponse(description='Nothing found, or not connected.'),
                   503: _DOWN},
    )
    @action(detail=False, methods=['get'], url_path='search', paginate_action=True)
    def search(self, request):
        """
        Search your photos

        Smart search by `query`, or the photos taken on a `date`.
        """
        integration = self.get_integration()
        params = validated(ImmichSearchQuerySerializer, request.query_params)
        arguments = {}
        if params.get('query'):
            arguments['query'] = params['query']
        if params.get('date'):
            arguments.update(self._build_date_range_arguments(params['date']))
        return self._fetch_immich_search_assets(
            integration, request, arguments, search_type='smart' if params.get('query') else 'metadata',
        )

    @extend_schema(
        responses={200: OpenApiResponse({'type': 'array', 'items': {'type': 'object'}},
                                        description="Immich's album objects, as Immich returns them."),
                   404: _NOT_CONNECTED, 503: _DOWN},
    )
    @action(detail=False, methods=['get'], pagination_class=None)
    def albums(self, request):
        """List your albums"""
        integration = self.get_integration()
        try:
            response = immich_get(f'{integration.server_url}/albums', headers={'x-api-key': integration.api_key},
                                  timeout=IMMICH_REQUEST_TIMEOUT)
            return Response(response.json())
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise _server_down()

    @extend_schema(
        parameters=[OpenApiParameter('album_id', str, OpenApiParameter.PATH, description='The Immich album id.')],
        responses={200: _paginated_assets(), 404: OpenApiResponse(description='Empty album, or not connected.'),
                   503: _DOWN},
    )
    @action(detail=False, methods=['get'], url_path=r'albums/(?P<album_id>[^/.]+)', paginate_action=True)
    def album(self, request, album_id=None):
        """List an album's photos"""
        integration = self.get_integration()
        try:
            response = immich_get(f'{integration.server_url}/albums/{album_id}',
                                  headers={'x-api-key': integration.api_key}, timeout=IMMICH_REQUEST_TIMEOUT)
            res = response.json()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise _server_down()

        album_assets = res.get('assets') if isinstance(res, dict) else None
        if isinstance(album_assets, list) and album_assets:
            return self._paginate_immich_assets(integration, request, album_assets)
        return self._fetch_immich_search_assets(
            integration, request, {'albumIds': [album_id]}, search_type='metadata',
            not_found_code='immich.no_assets_found',
        )

    @extend_schema(
        parameters=[
            OpenApiParameter('integration_id', OpenApiTypes.UUID, OpenApiParameter.PATH,
                             description='The Immich connection the photo comes from.'),
            OpenApiParameter('asset_id', str, OpenApiParameter.PATH, description='The Immich asset id.'),
        ],
        responses={
            (200, 'image/*'): OpenApiResponse(response=bytes, description='A preview-sized image.'),
            403: OpenApiResponse(description='The photo is on records you cannot see (`immich.permission_denied`).'),
            404: OpenApiResponse(description='Unknown connection, or the photo is not on any record (`immich.not_found`).'),
            502: OpenApiResponse(description='Immich did not return an image (`immich.invalid_content`).'),
            503: _DOWN,
            504: OpenApiResponse(description='Immich was too slow (`immich.timeout`).'),
        },
    )
    @action(
        detail=False, methods=['get'], url_path=r'assets/(?P<integration_id>[^/.]+)/(?P<asset_id>[^/.]+)',
        permission_classes=[AllowAny], throttle_classes=[ImageProxyThrottle],
    )
    def asset(self, request, integration_id=None, asset_id=None):
        """
        Show an Immich photo

        Serves a photo from the owner's Immich server. Anyone who can see a record the photo
        is on can load it, also without signing in for public records; the owner can load
        any photo from their server.
        """
        integration = ImmichIntegration.objects.filter(id=as_uuid(integration_id)).first() \
            if as_uuid(integration_id) else None
        if integration is None:
            raise NotFound('Immich connection not found.')
        owner = integration.user

        # Every photo of this Immich asset that the integration's owner has added somewhere
        image_entries = list(
            ContentImage.objects.filter(immich_id=asset_id, user=owner).select_related('content_type')
        )
        user = request.user if request.user.is_authenticated else None
        if user is None or user != owner:
            # The same rule as the rest of the app serves files by: members and guest links of
            # a collection, readers of its public story, and a place's own public flag.
            if not any(can_read_content_image(entry, user, request) for entry in image_entries):
                if image_entries:
                    raise APIError('This photo is private.', code='immich.permission_denied', status=403)
                raise APIError('This photo is not on any record you can see.', code='immich.not_found', status=404)

        try:
            immich_response = immich_get(
                f'{integration.server_url}/assets/{asset_id}/thumbnail?size=preview',
                headers={'x-api-key': integration.api_key},
                timeout=5,
            )
        except requests.exceptions.ConnectionError:
            raise _server_down()
        except requests.exceptions.Timeout:
            raise APIError('The Immich server took too long.', code='immich.timeout', status=504)

        content_type = immich_response.headers.get('Content-Type', 'image/jpeg')
        if not content_type.startswith('image/'):
            raise APIError('Immich did not return an image.', code='immich.invalid_content', status=502)
        response = HttpResponse(immich_response.content, content_type=content_type, status=200)
        # A shared cache may keep it only when the request needed no sign-in or link to pass.
        visibility = 'public' if user is None and not has_guest_token(request) else 'private'
        response['Cache-Control'] = f'{visibility}, max-age=86400, stale-while-revalidate=3600'
        return response
