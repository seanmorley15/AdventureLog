import logging

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from adventures.serializers import SearchHitSerializer
from adventures.services.search import SearchValidationError, global_search

logger = logging.getLogger(__name__)


class GlobalSearchView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        query = (request.query_params.get('q') or request.query_params.get('query') or '').strip()
        if not query:
            return Response({'error': 'Search query is required'}, status=400)

        types_param = request.query_params.get('types', '').strip()
        types = None
        if types_param:
            types = {item.strip() for item in types_param.split(',') if item.strip()}

        try:
            limit = int(request.query_params.get('limit', 20))
        except (TypeError, ValueError):
            return Response({'error': 'limit must be an integer'}, status=400)

        try:
            offset = int(request.query_params.get('offset', 0))
        except (TypeError, ValueError):
            return Response({'error': 'offset must be an integer'}, status=400)

        try:
            payload = global_search(
                user=request.user,
                query=query,
                types=types,
                limit=limit,
                offset=offset,
            )
        except SearchValidationError as exc:
            logger.warning('Global search validation failed: %s', exc.message)
            return Response({'error': exc.message}, status=400)

        serializer = SearchHitSerializer(payload['results'], many=True)
        return Response(
            {
                'query': payload['query'],
                'total': payload['total'],
                'limit': payload['limit'],
                'offset': payload['offset'],
                'results': serializer.data,
                'facets': payload['facets'],
            }
        )
