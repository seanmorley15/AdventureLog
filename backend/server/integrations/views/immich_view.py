import os
from rest_framework.response import Response
from rest_framework import viewsets, status
from integrations.serializers import ImmichIntegrationSerializer
from integrations.models import ImmichIntegration
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
import requests
from adventures.models import ContentImage
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from integrations.utils import StandardResultsSetPagination
import logging

logger = logging.getLogger(__name__)

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
            # Create date range for the entire selected day
            from datetime import datetime, timedelta
            try:
                # Parse the date and create start/end of day
                selected_date = datetime.strptime(date, '%Y-%m-%d')
                start_of_day = selected_date.strftime('%Y-%m-%d')
                end_of_day = (selected_date + timedelta(days=1)).strftime('%Y-%m-%d')
                
                arguments['takenAfter'] = start_of_day
                arguments['takenBefore'] = end_of_day
            except ValueError:
                return Response(
                    {
                        'message': 'Invalid date format. Use YYYY-MM-DD.',
                        'error': True,
                        'code': 'immich.invalid_date_format'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        # check so if the server is down, it does not tweak out like a madman and crash the server with a 500 error code
        try:
            url = f'{integration.server_url}/search/{"smart" if query else "metadata"}'
            immich_fetch = requests.post(url, headers={
                'x-api-key': integration.api_key
            },
            json = arguments
            )
            res = immich_fetch.json()
        except requests.exceptions.ConnectionError:
            return Response(
                {
                    'message': 'The Immich server is currently down or unreachable.',
                    'error': True,
                    'code': 'immich.server_down'
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
                
        if 'assets' in res and 'items' in res['assets']:
            paginator = self.pagination_class()
            # for each item in the items, we need to add the image url to the item so we can display it in the frontend
            public_url = os.environ.get('PUBLIC_URL', 'http://127.0.0.1:8000').rstrip('/')
            public_url = public_url.replace("'", "")
            for item in res['assets']['items']:
                item['image_url'] = f'{public_url}/api/integrations/immich/{integration.id}/get/{item["id"]}'
            result_page = paginator.paginate_queryset(res['assets']['items'], request)
            return paginator.get_paginated_response(result_page)
        else:
            return Response(
                {
                    'message': 'No items found.',
                    'error': True,
                    'code': 'immich.no_items_found'
                },
                status=status.HTTP_404_NOT_FOUND
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
            immich_fetch = requests.get(f'{integration.server_url}/albums', headers={
                'x-api-key': integration.api_key
            })
            res = immich_fetch.json()
        except requests.exceptions.ConnectionError:
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
        print(integration.user)
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
            immich_fetch = requests.get(f'{integration.server_url}/albums/{albumid}', headers={
                'x-api-key': integration.api_key
            })
            res = immich_fetch.json()
        except requests.exceptions.ConnectionError:
            return Response(
                {
                    'message': 'The Immich server is currently down or unreachable.',
                    'error': True,
                    'code': 'immich.server_down'
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        if 'assets' in res:
            paginator = self.pagination_class()
            # for each item in the items, we need to add the image url to the item so we can display it in the frontend
            public_url = os.environ.get('PUBLIC_URL', 'http://127.0.0.1:8000').rstrip('/')
            public_url = public_url.replace("'", "")
            for item in res['assets']:
                item['image_url'] = f'{public_url}/api/integrations/immich/{integration.id}/get/{item["id"]}'
            result_page = paginator.paginate_queryset(res['assets'], request)
            return paginator.get_paginated_response(result_page)
        else:
            return Response(
                {
                    'message': 'No assets found in this album.',
                    'error': True,
                    'code': 'immich.no_assets_found'
                },
                status=status.HTTP_404_NOT_FOUND
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

        # Get all images for this immich_id and user
        image_entries = list(
            ContentImage.objects
            .filter(immich_id=imageid, user=owner_id)
            .select_related('content_type')
        )

        # Sort by access level priority and find the best match
        def get_access_priority(image_entry):
            """Return priority score for access control (lower = higher priority)"""
            content_obj = image_entry.content_object
            
            # Only handle Location objects for now (can be extended for other types)
            if not hasattr(content_obj, 'is_public'):
                return 999  # Low priority for non-location objects
            
            # For Location objects, check access levels
            if content_obj.is_public:
                return 0  # Highest priority - public location
            
            # Check if location is in any public collection
            if hasattr(content_obj, 'collections'):
                collections = content_obj.collections.all()
                if any(collection.is_public for collection in collections):
                    return 1  # Second priority - private location in public collection
                    
                # Check for shared collections (if user is authenticated)
                if (request.user.is_authenticated and 
                    any(collection.shared_with.filter(id=request.user.id).exists() 
                        for collection in collections)):
                    return 2  # Third priority - shared collection access
            
            return 3  # Lowest priority - private location, owner access only

        # Sort image entries by access priority
        image_entries.sort(key=get_access_priority)
        image_entry = image_entries[0] if image_entries else None

        # Access control
        if image_entry:
            content_obj = image_entry.content_object
            
            # Only apply access control to Location objects
            if hasattr(content_obj, 'is_public'):
                location = content_obj
                
                # Determine access level
                is_authorized = False

                # Level 1: Public location (highest priority)
                if location.is_public:
                    is_authorized = True

                # Level 2: Private location in any public collection
                elif hasattr(location, 'collections'):
                    collections = location.collections.all()
                    if any(collection.is_public for collection in collections):
                        is_authorized = True
                    
                    # Level 3: Owner access
                    elif request.user.is_authenticated and request.user == owner_id:
                        is_authorized = True
                        
                    # Level 4: Shared collection access or collection owner access
                    elif (request.user.is_authenticated and 
                        (any(collection.shared_with.filter(id=request.user.id).exists() 
                            for collection in collections) or
                         any(collection.user == request.user for collection in collections))):
                        is_authorized = True
                else:
                    # Location without collections - owner access only
                    if request.user.is_authenticated and request.user == owner_id:
                        is_authorized = True
                
                if not is_authorized:
                    return Response({
                        'message': 'This image belongs to a private location and you are not authorized.',
                        'error': True,
                        'code': 'immich.permission_denied'
                    }, status=status.HTTP_403_FORBIDDEN)
            else:
                # For non-Location objects, allow only owner access for now
                if not request.user.is_authenticated or request.user != owner_id:
                    return Response({
                        'message': 'This image is not publicly accessible and you are not the owner.',
                        'error': True,
                        'code': 'immich.permission_denied'
                    }, status=status.HTTP_403_FORBIDDEN)
        else:
            # No ContentImage exists; allow only the integration owner
            if not request.user.is_authenticated or request.user != owner_id:
                return Response({
                    'message': 'Image is not linked to any location and you are not the owner.',
                    'error': True,
                    'code': 'immich.not_found'
                }, status=status.HTTP_404_NOT_FOUND)

        # Fetch from Immich
        try:
            immich_response = requests.get(
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
            response['Cache-Control'] = 'public, max-age=86400, stale-while-revalidate=3600'
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
        
        # Remove trailing slash if present
        original_server_url = server_url.rstrip('/')
        
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
                response = requests.get(
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