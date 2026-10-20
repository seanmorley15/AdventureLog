import os
from datetime import datetime, timedelta

from rest_framework.response import Response
from rest_framework import viewsets, status
from integrations.serializers import ImmichIntegrationSerializer
from core.net import self_hosted_session
from integrations.errors import IntegrationError
from integrations.services import server_urls
from integrations.models import ImmichIntegration
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
import requests
from adventures.models import ContentImage
from adventures.access.audience import has_guest_token
from adventures.access.file_permissions import can_read_content_image
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from core.pagination import StandardResultsSetPagination
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


class ImmichIntegrationView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def check_integration(self, request):
        """
        Checks if the user has an active Immich integration.
        Returns:
            - The integration object if it exists.
            - A Response with an error message if the integration is missing.
        """
        if not request.user.is_authenticated:
            return Response(
                {
                    'message': 'You need to be authenticated to use this feature.',
                    'error': True,
                    'code': 'immich.authentication_required'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        user_integrations = ImmichIntegration.objects.filter(user=request.user)
        if not user_integrations.exists():
            return Response(
                {
                    'message': 'You need to have an active Immich integration to use this feature.',
                    'error': True,
                    'code': 'immich.integration_missing'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        return user_integrations.first()

    def _immich_connection_error(self):
        return Response(
            {
                'message': 'The Immich server is currently down or unreachable.',
                'error': True,
                'code': 'immich.server_down'
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    def _immich_no_items_error(self, code='immich.no_items_found', message='No items found.'):
        return Response(
            {
                'message': message,
                'error': True,
                'code': code
            },
            status=status.HTTP_404_NOT_FOUND
        )

    def _build_date_range_arguments(self, date):
        selected_date = datetime.strptime(date, '%Y-%m-%d')
        next_day = selected_date + timedelta(days=1)
        return {
            'takenAfter': f'{selected_date.strftime("%Y-%m-%d")}T00:00:00.000Z',
            'takenBefore': f'{next_day.strftime("%Y-%m-%d")}T00:00:00.000Z',
        }

    def _paginate_immich_assets(self, integration, request, items):
        public_url = os.environ.get('PUBLIC_URL', 'http://127.0.0.1:8000').rstrip('/')
        public_url = public_url.replace("'", "")
        for item in items:
            item['image_url'] = f'{public_url}/api/integrations/immich/{integration.id}/get/{item["id"]}'

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
                return self._immich_connection_error()

            if not immich_fetch.ok:
                logger.warning(
                    'Immich search request failed: status=%s response=%s',
                    immich_fetch.status_code,
                    res,
                )
                return self._immich_no_items_error(code=not_found_code)

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

        return self._immich_no_items_error(code=not_found_code)

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """
        Handles the logic for searching Immich images.
        """
        # Check for integration before proceeding
        integration = self.check_integration(request)
        if isinstance(integration, Response):
            return integration
                
        query = request.query_params.get('query', '')
        date = request.query_params.get('date', '')

        if not query and not date:
            return Response(
                {
                    'message': 'Query or date is required.',
                    'error': True,
                    'code': 'immich.query_required'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
                
        arguments = {}
        if query:
            arguments['query'] = query
        if date:
            try:
                arguments.update(self._build_date_range_arguments(date))
            except ValueError:
                return Response(
                    {
                        'message': 'Invalid date format. Use YYYY-MM-DD.',
                        'error': True,
                        'code': 'immich.invalid_date_format'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        return self._fetch_immich_search_assets(
            integration,
            request,
            arguments,
            search_type='smart' if query else 'metadata',
        )
        
    @action(detail=False, methods=['get'])
    def albums(self, request):
        """
        RESTful GET method for retrieving all Immich albums.
        """
        # Check for integration before proceeding
        integration = self.check_integration(request)
        if isinstance(integration, Response):
            return integration

        # check so if the server is down, it does not tweak out like a madman and crash the server with a 500 error code
        try:
            immich_fetch = immich_get(f'{integration.server_url}/albums', headers={
                'x-api-key': integration.api_key
            }, timeout=IMMICH_REQUEST_TIMEOUT)
            res = immich_fetch.json()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            return Response(
                {
                    'message': 'The Immich server is currently down or unreachable.',
                    'error': True,
                    'code': 'immich.server_down'
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        return Response(
            res,
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'], url_path='albums/(?P<albumid>[^/.]+)')
    def album(self, request, albumid=None):
        """
        RESTful GET method for retrieving a specific Immich album by ID.
        """
        # Check for integration before proceeding
        integration = self.check_integration(request)
        if isinstance(integration, Response):
            return integration

        if not albumid:
            return Response(
                {
                    'message': 'Album ID is required.',
                    'error': True,
                    'code': 'immich.albumid_required'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # check so if the server is down, it does not tweak out like a madman and crash the server with a 500 error code
        try:
            immich_fetch = immich_get(f'{integration.server_url}/albums/{albumid}', headers={
                'x-api-key': integration.api_key
            }, timeout=IMMICH_REQUEST_TIMEOUT)
            res = immich_fetch.json()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            return Response(
                {
                    'message': 'The Immich server is currently down or unreachable.',
                    'error': True,
                    'code': 'immich.server_down'
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        album_assets = res.get('assets')
        if isinstance(album_assets, list) and album_assets:
            return self._paginate_immich_assets(integration, request, album_assets)

        return self._fetch_immich_search_assets(
            integration,
            request,
            {'albumIds': [albumid]},
            search_type='metadata',
            not_found_code='immich.no_assets_found',
        )

    @action(
    detail=False,
    methods=['get'],
    url_path='(?P<integration_id>[^/.]+)/get/(?P<imageid>[^/.]+)',
    permission_classes=[]
    )
    def get_by_integration(self, request, integration_id=None, imageid=None):
        """
        GET an Immich image using the integration and asset ID.
        Access levels (in order of priority):
        1. Public locations: accessible by anyone
        2. Private locations in public collections: accessible by anyone
        3. Private locations in private collections shared with user: accessible by shared users, and the collection owner
        4. Private locations: accessible only to the owner
        5. No ContentImage: owner can still view via integration
        """
        if not imageid or not integration_id:
            return Response({
                'message': 'Image ID and Integration ID are required.',
                'error': True,
                'code': 'immich.missing_params'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Lookup integration and user
        integration = get_object_or_404(ImmichIntegration, id=integration_id)
        owner_id = integration.user

        # Every photo of this Immich asset that the integration's owner has added somewhere
        image_entries = list(
            ContentImage.objects
            .filter(immich_id=imageid, user=owner_id)
            .select_related('content_type')
        )

        user = request.user if request.user.is_authenticated else None
        if user is None or user != owner_id:
            # The same rule as the rest of the app serves files by: members and guest links of
            # a collection, readers of its public story, and a place's own public flag.
            if not any(can_read_content_image(entry, user, request) for entry in image_entries):
                if image_entries:
                    return Response({
                        'message': 'This image is private and you are not authorized.',
                        'error': True,
                        'code': 'immich.permission_denied'
                    }, status=status.HTTP_403_FORBIDDEN)
                return Response({
                    'message': 'Image is not linked to any location and you are not the owner.',
                    'error': True,
                    'code': 'immich.not_found'
                }, status=status.HTTP_404_NOT_FOUND)

        # Fetch from Immich
        try:
            immich_response = immich_get(
                f'{integration.server_url}/assets/{imageid}/thumbnail?size=preview',
                headers={'x-api-key': integration.api_key},
                timeout=5
            )
            content_type = immich_response.headers.get('Content-Type', 'image/jpeg')
            if not content_type.startswith('image/'):
                return Response({
                    'message': 'Invalid content type returned from Immich.',
                    'error': True,
                    'code': 'immich.invalid_content'
                }, status=status.HTTP_502_BAD_GATEWAY)

            response = HttpResponse(immich_response.content, content_type=content_type, status=200)
            # A shared cache may keep it only when the request needed no sign-in or link to pass.
            visibility = 'public' if user is None and not has_guest_token(request) else 'private'
            response['Cache-Control'] = f'{visibility}, max-age=86400, stale-while-revalidate=3600'
            return response

        except requests.exceptions.ConnectionError:
            return Response({
                'message': 'The Immich server is unreachable.',
                'error': True,
                'code': 'immich.server_down'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        except requests.exceptions.Timeout:
            return Response({
                'message': 'The Immich server request timed out.',
                'error': True,
                'code': 'immich.timeout'
            }, status=status.HTTP_504_GATEWAY_TIMEOUT)

class ImmichIntegrationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ImmichIntegrationSerializer
    queryset = ImmichIntegration.objects.all()

    def get_queryset(self):
        return ImmichIntegration.objects.filter(user=self.request.user)

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

    def create(self, request):
        """
        RESTful POST method for creating a new Immich integration.
        """
        # Check if the user already has an integration
        user_integrations = ImmichIntegration.objects.filter(user=request.user)
        if user_integrations.exists():
            return Response(
                {
                    'message': 'You already have an active Immich integration.',
                    'error': True,
                    'code': 'immich.integration_exists'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            # Validate Immich server connection before saving
            server_url = serializer.validated_data.get('server_url')
            api_key = serializer.validated_data.get('api_key')
            
            is_valid, corrected_server_url, error_message = self._validate_immich_connection(server_url, api_key)
            
            if not is_valid:
                return Response(
                    {
                        'message': f'Cannot connect to Immich server: {error_message}',
                        'error': True,
                        'code': 'immich.connection_failed',
                        'details': error_message
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # If validation passes, save the integration with the corrected URL
            serializer.save(user=request.user, server_url=corrected_server_url)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def update(self, request, pk=None):
        """
        RESTful PUT method for updating an existing Immich integration.
        """
        integration = ImmichIntegration.objects.filter(user=request.user, id=pk).first()
        if not integration:
            return Response(
                {
                    'message': 'Integration not found.',
                    'error': True,
                    'code': 'immich.integration_not_found'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.serializer_class(integration, data=request.data, partial=True)
        if serializer.is_valid():
            # Validate Immich server connection before updating
            server_url = serializer.validated_data.get('server_url', integration.server_url)
            api_key = serializer.validated_data.get('api_key', integration.api_key)
            
            is_valid, corrected_server_url, error_message = self._validate_immich_connection(server_url, api_key)
            
            if not is_valid:
                return Response(
                    {
                        'message': f'Cannot connect to Immich server: {error_message}',
                        'error': True,
                        'code': 'immich.connection_failed',
                        'details': error_message
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # If validation passes, save the integration with the corrected URL
            serializer.save(server_url=corrected_server_url)
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def destroy(self, request, pk=None):
        """
        RESTful DELETE method for deleting an existing Immich integration.
        """
        integration = ImmichIntegration.objects.filter(user=request.user, id=pk).first()
        if not integration:
            return Response(
                {
                    'message': 'Integration not found.',
                    'error': True,
                    'code': 'immich.integration_not_found'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        integration.delete()
        return Response(
            {
                'message': 'Integration deleted successfully.'
            },
            status=status.HTTP_200_OK
        )

    def list(self, request, *args, **kwargs):
        # If the user has an integration, we only want to return that integration
        user_integrations = ImmichIntegration.objects.filter(user=request.user)
        if user_integrations.exists():
            integration = user_integrations.first()
            serializer = self.serializer_class(integration)
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {
                    'message': 'No integration found.',
                    'error': True,
                    'code': 'immich.integration_not_found'
                },
                status=status.HTTP_404_NOT_FOUND
            )