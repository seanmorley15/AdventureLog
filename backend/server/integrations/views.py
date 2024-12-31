from rest_framework.response import Response
from rest_framework import viewsets, status
from .models import ImmichIntegration
from rest_framework.decorators import action
import requests

class ImmichIntegrationView(viewsets.ViewSet):
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
        
        
        immich_fetch = requests.post(f'{integration.server_url}/search/smart', headers={
            'x-api-key': integration.api_key
        },
        json = {
            'query': query
        }
        )
        res = immich_fetch.json()
                
        if 'assets' in res and 'items' in res['assets']:
            return Response(res['assets']['items'], status=status.HTTP_200_OK)
        else:
            return Response(
                {
                    'message': 'No items found.',
                    'error': True,
                    'code': 'immich.no_items_found'
                },
                status=status.HTTP_404_NOT_FOUND
            )
    


    def get(self, request):
        """
        RESTful GET method for searching Immich images.
        """
        return self.search(request)
