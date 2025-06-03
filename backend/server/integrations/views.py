import os
from rest_framework.response import Response
from rest_framework import viewsets, status
from .serializers import ImmichIntegrationSerializer
from .models import ImmichIntegration
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
import requests
from rest_framework.pagination import PageNumberPagination
from django.conf import settings
from adventures.models import AdventureImage
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

class IntegrationView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    def list(self, request):
        """
        RESTful GET method for listing all integrations.
        """
        immich_integrations = ImmichIntegration.objects.filter(user=request.user)
        google_map_integration = settings.GOOGLE_MAPS_API_KEY != ''

        return Response(
            {
                'immich': immich_integrations.exists(),
                'google_maps': google_map_integration
            },
            status=status.HTTP_200_OK
        )

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 1000

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
        1. Public adventures: accessible by anyone
        2. Private adventures in public collections: accessible by anyone
        3. Private adventures in private collections shared with user: accessible by shared users
        4. Private adventures: accessible only to the owner
        5. No AdventureImage: owner can still view via integration
        """
        if not imageid or not integration_id:
            return Response({
                'message': 'Image ID and Integration ID are required.',
                'error': True,
                'code': 'immich.missing_params'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Lookup integration and user
        integration = get_object_or_404(ImmichIntegration, id=integration_id)
        owner_id = integration.user_id

        # Try to find the image entry with collection and sharing information
        image_entry = (
            AdventureImage.objects
            .filter(immich_id=imageid, user_id=owner_id)
            .select_related('adventure', 'adventure__collection')
            .prefetch_related('adventure__collection__shared_with')
            .order_by(
                '-adventure__is_public',  # Public adventures first
                '-adventure__collection__is_public'  # Then public collections
            )
            .first()
        )

        # Access control
        if image_entry:
            adventure = image_entry.adventure
            collection = adventure.collection
            
            # Determine access level
            is_authorized = False
            
            # Level 1: Public adventure (highest priority)
            if adventure.is_public:
                is_authorized = True
                
            # Level 2: Private adventure in public collection
            elif collection and collection.is_public:
                is_authorized = True
                
            # Level 3: Owner access
            elif request.user.is_authenticated and request.user.id == owner_id:
                is_authorized = True
                
            # Level 4: Shared collection access
            elif (request.user.is_authenticated and collection and 
                collection.shared_with.filter(id=request.user.id).exists()):
                is_authorized = True
            
            if not is_authorized:
                return Response({
                    'message': 'This image belongs to a private adventure and you are not authorized.',
                    'error': True,
                    'code': 'immich.permission_denied'
                }, status=status.HTTP_403_FORBIDDEN)
        else:
            # No AdventureImage exists; allow only the integration owner
            if not request.user.is_authenticated or request.user.id != owner_id:
                return Response({
                    'message': 'Image is not linked to any adventure and you are not the owner.',
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
            serializer.save(user=request.user)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
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