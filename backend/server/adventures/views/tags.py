from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.response import Response

from adventures.models import Location


class TagViewSet(viewsets.ViewSet):
    openapi_tags = ['Categories & tags']

    @extend_schema(responses={200: {'type': 'array', 'items': {'type': 'string'}}})
    def list(self, request):
        """
        List your tags

        Every distinct tag used on your locations, for suggestions while editing.
        """
        tags = []
        for location_tags in Location.objects.filter(user=request.user).values_list('tags', flat=True).distinct():
            for tag in location_tags or []:
                if tag and tag not in tags:
                    tags.append(tag)
        return Response(tags)
