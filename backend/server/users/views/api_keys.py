"""Creating, listing and revoking API keys."""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import APIKey
from users.serializers import APIKeyCreateSerializer, APIKeyCreatedSerializer, APIKeySerializer


class APIKeyListCreateView(APIView):
    openapi_tags = ['Account']

    @extend_schema(responses=APIKeySerializer(many=True))
    def get(self, request):
        """
        List your API keys

        Each key shows its name and the first characters (`key_prefix`) so you can tell them
        apart. The key itself is never shown again after it is created. The mobile app's key is
        listed too.
        """
        keys = APIKey.objects.filter(user=request.user)
        return Response(APIKeySerializer(keys, many=True).data)

    @extend_schema(request=APIKeyCreateSerializer, responses={201: APIKeyCreatedSerializer})
    def post(self, request):
        """
        Create an API key

        The response carries the full `key` **once**. Store it now: only a hash is kept on the
        server. Send it as `X-API-Key: <key>` or `Authorization: Api-Key <key>`.
        """
        serializer = APIKeyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        api_key, raw_key = APIKey.generate(user=request.user, name=serializer.validated_data['name'])
        data = APIKeySerializer(api_key).data
        data['key'] = raw_key
        return Response(data, status=status.HTTP_201_CREATED)


class APIKeyDetailView(APIView):
    openapi_tags = ['Account']

    @extend_schema(responses={204: OpenApiResponse(description='The key was revoked and stops working at once.')})
    def delete(self, request, pk):
        """Revoke an API key"""
        get_object_or_404(APIKey, pk=pk, user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
