from drf_spectacular.utils import extend_schema
from rest_framework import serializers, viewsets
from rest_framework.response import Response

from adventures.serializers import SearchHitSerializer
from adventures.services.search import global_search
from core.serializers import validated


class SearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(help_text='Words to look for (two characters or more each).')
    types = serializers.CharField(
        required=False,
        help_text='Comma-separated kinds to search, e.g. `location,collection`. All by default.',
    )
    limit = serializers.IntegerField(default=20, min_value=1, max_value=100)
    offset = serializers.IntegerField(default=0, min_value=0)


class SearchResponseSerializer(serializers.Serializer):
    query = serializers.CharField()
    count = serializers.IntegerField(help_text='Matches across all kinds, before `limit` and `offset`.')
    limit = serializers.IntegerField()
    offset = serializers.IntegerField()
    results = SearchHitSerializer(many=True)
    facets = serializers.DictField(child=serializers.IntegerField(), help_text='Matches per kind.')


class SearchViewSet(viewsets.ViewSet):
    openapi_tags = ['Search']

    @extend_schema(parameters=[SearchQuerySerializer], responses=SearchResponseSerializer)
    def list(self, request):
        """
        Search everything

        Locations, collections, lodging, transportation, notes, checklists, activities,
        countries, regions, cities and people you can see, best matches first.
        """
        params = validated(SearchQuerySerializer, request.query_params)
        types = {item.strip() for item in params.get('types', '').split(',') if item.strip()} or None
        payload = global_search(
            user=request.user, query=params['q'].strip(), types=types, limit=params['limit'], offset=params['offset']
        )
        return Response({
            'query': payload['query'],
            'count': payload['total'],
            'limit': payload['limit'],
            'offset': payload['offset'],
            'results': SearchHitSerializer(payload['results'], many=True).data,
            'facets': payload['facets'],
        })
