import os
from rest_framework.response import Response
from rest_framework import viewsets, status
from .models import ImmichIntegration
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
import requests
from rest_framework.pagination import PageNumberPagination

class IntegrationView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    def list(self, request):
        """
        RESTful GET method for listing all integrations.
        """
        immich_integrations = ImmichIntegration.objects.filter(user=request.user)

        return Response(
            {
                'immich': immich_integrations.exists()
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

        if not query:
            return Response(
                {
                    'message': 'Query is required.',
                    'error': True,
                    'code': 'immich.query_required'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # check so if the server is down, it does not tweak out like a madman and crash the server with a 500 error code
        try:
            immich_fetch = requests.post(f'{integration.server_url}/search/smart', headers={
                'x-api-key': integration.api_key
            },
            json = {
                'query': query
            }
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
    
    @action(detail=False, methods=['get'], url_path='get/(?P<imageid>[^/.]+)')
    def get(self, request, imageid=None):
        """
        RESTful GET method for retrieving a specific Immich image by ID.
        """
        # Check for integration before proceeding
        integration = self.check_integration(request)
        if isinstance(integration, Response):
            return integration

        if not imageid:
            return Response(
                {
                    'message': 'Image ID is required.',
                    'error': True,
                    'code': 'immich.imageid_required'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # check so if the server is down, it does not tweak out like a madman and crash the server with a 500 error code
        try:
            immich_fetch = requests.get(f'{integration.server_url}/assets/{imageid}/thumbnail?size=preview', headers={
                'x-api-key': integration.api_key
            })
            # should return the image file
            from django.http import HttpResponse
            return HttpResponse(immich_fetch.content, content_type='image/jpeg', status=status.HTTP_200_OK)
        except requests.exceptions.ConnectionError:
            return Response(
                {
                    'message': 'The Immich server is currently down or unreachable.',
                    'error': True,
                    'code': 'immich.server_down'
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
