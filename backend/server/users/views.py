from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import ChangeEmailSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.conf import settings

class ChangeEmailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=ChangeEmailSerializer,
        responses={
            200: openapi.Response('Email successfully changed'),
            400: 'Bad Request'
        },
        operation_description="Change the email address for the authenticated user."
    )
    def post(self, request):
        serializer = ChangeEmailSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            new_email = serializer.validated_data['new_email']
            user.email = new_email
            # remove all other email addresses for the user
            user.emailaddress_set.exclude(email=new_email).delete()
            user.emailaddress_set.create(email=new_email, primary=True, verified=False)
            user.save()
            return Response({"detail": "Email successfully changed."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class IsRegistrationDisabled(APIView):
    @swagger_auto_schema(
        responses={
            200: openapi.Response('Registration is disabled'),
            400: 'Bad Request'
        },
        operation_description="Check if registration is disabled."
    )
    def get(self, request):
        return Response({"is_disabled": settings.DISABLE_REGISTRATION}, status=status.HTTP_200_OK)
    