from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from adventures.services.visited_regions import sync_visited_regions


class VisitedRegionSyncView(APIView):
    openapi_tags = ['World travel']

    @extend_schema(
        request=None,
        responses=inline_serializer('VisitedRegionSync', fields={
            'new_regions': serializers.IntegerField(),
            'regions': serializers.DictField(child=serializers.CharField(), help_text='Newly marked regions: id → name.'),
            'new_cities': serializers.IntegerField(),
            'cities': serializers.DictField(child=serializers.CharField(), help_text='Newly marked cities: id → name.'),
        }),
    )
    def post(self, request):
        """
        Mark regions visited from your places

        Marks the region and city of every location you have visited, using the place data
        already stored, and returns the ones that were new.
        """
        return Response(sync_visited_regions(request.user))
