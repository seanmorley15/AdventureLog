"""Public profiles: who can be found, and what is shown about them."""

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from adventures.models import Collection, Location
from adventures.serializers import LocationSerializer, UltraSlimCollectionSerializer
from adventures.services.user_stats import UserStatsService
from users.serializers import PublicProfileSerializer, UserStatsSerializer

User = get_user_model()
_stats_service = UserStatsService()


def _visible_user(request, username):
    """A user with a public profile, or the requester themselves. Anyone else is a 404."""
    if request.user.is_authenticated and request.user.username == username:
        return get_object_or_404(User, username=username)
    return get_object_or_404(User, username=username, public_profile=True)


class PublicUserListView(APIView):
    openapi_tags = ['Users']
    permission_classes = [AllowAny]

    @extend_schema(responses=PublicProfileSerializer(many=True))
    def get(self, request):
        """
        List public profiles

        Everyone who made their profile public, except you.
        """
        users = User.objects.filter(public_profile=True)
        if request.user.is_authenticated:
            users = users.exclude(id=request.user.id)
        return Response(PublicProfileSerializer(users, many=True).data)


class PublicUserDetailView(APIView):
    openapi_tags = ['Users']
    permission_classes = [AllowAny]

    @extend_schema(
        responses=inline_serializer(
            'PublicProfileDetail',
            fields={
                'user': PublicProfileSerializer(),
                'locations': LocationSerializer(many=True, help_text='Their public locations.'),
                'collections': UltraSlimCollectionSerializer(
                    many=True, help_text='Their collections whose visibility is `public`, as cards.'
                ),
            },
        )
    )
    def get(self, request, username):
        """
        Get a public profile

        The user, their public locations, and their public collections. Private profiles are
        404 to everyone but their owner.
        """
        user = _visible_user(request, username)
        # A location is listed by its own flag. A collection is listed only when its
        # visibility is public, and as a card: the private plan is not part of a profile.
        locations = Location.objects.filter(user=user, is_public=True)
        collections = Collection.objects.filter(user=user, visibility=Collection.Visibility.PUBLIC)
        return Response({
            'user': PublicProfileSerializer(user).data,
            'locations': LocationSerializer(locations, many=True, context={'request': request}).data,
            'collections': UltraSlimCollectionSerializer(collections, many=True, context={'request': request}).data,
        })


class PublicUserStatsView(APIView):
    openapi_tags = ['Users']
    permission_classes = [AllowAny]

    @extend_schema(responses=UserStatsSerializer)
    def get(self, request, username):
        """
        Get a user's travel stats

        Counts of places, trips, visited countries, regions and cities, and activity totals.
        Available for public profiles and for yourself.
        """
        user = _visible_user(request, username)
        return Response(_stats_service.build_user_stats(user, request.user, include_categories=True))


__all__ = ['PublicUserDetailView', 'PublicUserListView', 'PublicUserStatsView']
