"""Creating, listing and revoking API keys."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from users.serializers import APIKeySerializer, APIKeyCreateSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.shortcuts import get_object_or_404
from users.models import APIKey


class APIKeyListCreateView(APIView):
    """
    List the current user's API keys or create a new one.

    GET  /auth/api-keys/   → list of keys (name, prefix, created_at, last_used_at)
    POST /auth/api-keys/   → create a new key; returns the raw token **once**
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={200: APIKeySerializer(many=True)},
        operation_description="List all API keys for the authenticated user.",
    )
    def get(self, request):
        keys = APIKey.objects.filter(user=request.user)
        serializer = APIKeySerializer(keys, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=APIKeyCreateSerializer,
        responses={
            201: openapi.Response(
                "API key created.  The ``key`` field is returned only once.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_STRING, format="uuid"),
                        "name": openapi.Schema(type=openapi.TYPE_STRING),
                        "key_prefix": openapi.Schema(type=openapi.TYPE_STRING),
                        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                        "last_used_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time", x_nullable=True),
                        "key": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Full API key – shown once, never stored.",
                        ),
                    },
                ),
            ),
            400: "Bad request – name is required.",
        },
        operation_description="Create a new API key.  Copy the returned ``key`` immediately; it will not be shown again.",
    )
    def post(self, request):
        serializer = APIKeyCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        api_key, raw_key = APIKey.generate(
            user=request.user,
            name=serializer.validated_data["name"],
        )
        response_data = APIKeySerializer(api_key).data
        response_data["key"] = raw_key
        return Response(response_data, status=status.HTTP_201_CREATED)


class APIKeyDetailView(APIView):
    """
    DELETE /auth/api-keys/<id>/  → revoke (delete) an API key
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            204: "API key deleted.",
            404: "Not found.",
        },
        operation_description="Revoke an API key by its ID.",
    )
    def delete(self, request, pk):
        api_key = get_object_or_404(APIKey, pk=pk, user=request.user)
        api_key.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
