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
            - None if the integration exists.
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
        return ImmichIntegration.objects.first()

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
            arguments['takenBefore'] = date

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
                item['image_url'] = f'{public_url}/api/integrations/immich/get/{item["id"]}'
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
                item['image_url'] = f'{public_url}/api/integrations/immich/get/{item["id"]}'
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

    @action(detail=False, methods=['get'], url_path='get/(?P<imageid>[^/.]+)', permission_classes=[])
    def get(self, request, imageid=None):
        """
        RESTful GET method for retrieving a specific Immich image by ID.
        Allows access to images for public adventures even if the user doesn't have Immich integration.
        """
        if not imageid:
            return Response(
                {
                    'message': 'Image ID is required.',
                    'error': True,
                    'code': 'immich.imageid_required'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if the image ID is associated with a public adventure
        
        public_image = AdventureImage.objects.filter(
            immich_id=imageid,
            adventure__is_public=True
        ).first()
        
        # If it's a public adventure image, use any available integration
        if public_image:
            integration = ImmichIntegration.objects.filter(
                user_id=public_image.adventure.user_id
            ).first()
            if not integration:
                return Response(
                    {
                        'message': 'No Immich integration available for public access.',
                        'error': True,
                        'code': 'immich.no_integration'
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
        else:
            # Not a public image, check user's integration
            integration = self.check_integration(request)
            if isinstance(integration, Response):
                return integration
        
        # Proceed with fetching the image
        try:
            immich_fetch = requests.get(
                f'{integration.server_url}/assets/{imageid}/thumbnail?size=preview', 
                headers={'x-api-key': integration.api_key},
                timeout=5  # Add timeout to prevent hanging
            )
            response = HttpResponse(immich_fetch.content, content_type='image/jpeg', status=status.HTTP_200_OK)
            response['Cache-Control'] = 'public, max-age=86400, stale-while-revalidate=3600'
            return response
        except requests.exceptions.ConnectionError:
            return Response(
                {
                    'message': 'The Immich server is currently down or unreachable.',
                    'error': True,
                    'code': 'immich.server_down'
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except requests.exceptions.Timeout:
            return Response(
                {
                    'message': 'The Immich server request timed out.',
                    'error': True,
                    'code': 'immich.server_timeout'
                },
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )

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