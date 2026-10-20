"""The QR code that signs the mobile app in."""

from os import getenv
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from users.serializers import APIKeySerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.conf import settings
from users.models import APIKey
import qrcode
import io
import base64
import json
from datetime import datetime


class MobileQRCodeView(APIView):
    """
    POST /auth/mobile-qr/  → generate a QR code for mobile app login
    GET  /auth/mobile-qr/  → get the current mobile API key if one exists
    DELETE /auth/mobile-qr/ → delete the mobile API key if one exists
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                "Mobile API key already exists",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_STRING, format="uuid"),
                        "name": openapi.Schema(type=openapi.TYPE_STRING),
                        "key_prefix": openapi.Schema(type=openapi.TYPE_STRING),
                        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                    },
                ),
            ),
            404: "No mobile API key found",
        },
        operation_description="Get the current mobile API key if one exists.",
    )
    def get(self, request):
        # Check if user already has a mobile app API key
        mobile_key = APIKey.objects.filter(
            user=request.user,
            name__startswith="Mobile App -"
        ).first()

        if mobile_key:
            serializer = APIKeySerializer(mobile_key)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(
            {"detail": "No mobile API key found."},
            status=status.HTTP_404_NOT_FOUND
        )

    @swagger_auto_schema(
        responses={
            201: openapi.Response(
                "QR code generated successfully",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_STRING, format="uuid"),
                        "name": openapi.Schema(type=openapi.TYPE_STRING),
                        "key_prefix": openapi.Schema(type=openapi.TYPE_STRING),
                        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                        "key": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Full API key – shown once, never stored.",
                        ),
                        "qr_code": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Base64-encoded PNG QR code image",
                        ),
                    },
                ),
            ),
            400: "Mobile API key already exists",
        },
        operation_description="Generate a QR code for mobile app login. Creates an API key with name 'Mobile App - [date]'.",
    )
    def post(self, request):
        # Check if user already has a mobile app API key
        existing_key = APIKey.objects.filter(
            user=request.user,
            name__startswith="Mobile App -"
        ).first()

        if existing_key:
            return Response(
                {"detail": "Mobile API key already exists. Please delete the existing one first."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate a new API key with a name like "Mobile App - March 17, 2026"
        name = f"Mobile App - {datetime.now().strftime('%B %d, %Y')}"
        api_key, raw_key = APIKey.generate(user=request.user, name=name)

        # Create QR code data with proper structure for mobile app
        qr_data = {
            "version": 1,
            "server_url": getattr(settings, 'PUBLIC_URL', getenv('PUBLIC_URL', 'http://localhost:8000')),
            "api_key": raw_key,
            "code_words": ["hike", "explore"]
        }

        # Generate QR code containing the JSON data
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)

        # Create QR code image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()

        # Return API key info and QR code
        response_data = APIKeySerializer(api_key).data
        response_data["key"] = raw_key
        response_data["qr_code"] = f"data:image/png;base64,{img_str}"

        return Response(response_data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        responses={
            204: "Mobile API key deleted.",
            404: "No mobile API key found.",
        },
        operation_description="Delete the mobile API key.",
    )
    def delete(self, request):
        # Find and delete the mobile app API key
        mobile_key = APIKey.objects.filter(
            user=request.user,
            name__startswith="Mobile App -"
        ).first()

        if not mobile_key:
            return Response(
                {"detail": "No mobile API key found."},
                status=status.HTTP_404_NOT_FOUND
            )

        mobile_key.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
