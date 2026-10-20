"""Public profiles: who can be found, and what is shown about them."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from users.serializers import CustomUserDetailsSerializer as PublicUserSerializer, without_private_fields
from adventures.serializers import LocationSerializer, UltraSlimCollectionSerializer
from adventures.models import Location, Collection


User = get_user_model()


class PublicUserListView(APIView):
    # Allow the listing of all public users
    permission_classes = []

    @swagger_auto_schema(
        responses={
            200: openapi.Response('List of public users'),
            400: 'Bad Request'
        },
        operation_description="List public users."
    )
    def get(self, request):
        users = User.objects.filter(public_profile=True).exclude(id=request.user.id)
        serializer = PublicUserSerializer(users, many=True)
        return Response([without_private_fields(user) for user in serializer.data], status=status.HTTP_200_OK)


class PublicUserDetailView(APIView):
    # Allow the retrieval of a single public user
    permission_classes = []

    @swagger_auto_schema(
        responses={
            200: openapi.Response('Public user information'),
            400: 'Bad Request'
        },
        operation_description="Get public user information."
    )
    def get(self, request, username):
        if request.user.username == username:
            user = get_object_or_404(User, username=username)
        else:
            user = get_object_or_404(User, username=username, public_profile=True)
        serializer = PublicUserSerializer(user)
        user_data = without_private_fields(serializer.data)

        # Get the users adventures and collections to include in the response
        # A location is listed by its own flag. A collection is listed only when its
        # visibility is public, and as a card: the private plan is not part of a profile.
        adventures = Location.objects.filter(user=user, is_public=True)
        collections = Collection.objects.filter(user=user, visibility=Collection.Visibility.PUBLIC)
        adventure_serializer = LocationSerializer(adventures, many=True)
        collection_serializer = UltraSlimCollectionSerializer(collections, many=True, context={'request': request})

        return Response({
            'user': user_data,
            'adventures': adventure_serializer.data,
            'collections': collection_serializer.data
        }, status=status.HTTP_200_OK)
