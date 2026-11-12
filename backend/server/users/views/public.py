"""Public profiles: who can be found, and what is shown about them."""

from django.contrib.auth import get_user_model
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from adventures.models import Collection, Location
from adventures.serializers import LocationSerializer, UltraSlimCollectionSerializer
from adventures.services.user_stats import UserStatsService
from core.visibility import can_see_profile, visible_profiles_q
from users.serializers import PublicProfileSerializer, UserStatsSerializer

User = get_user_model()
_stats_service = UserStatsService()


def _visible_user(request, username):
    """
    A user whose profile the requester may see: their own, one shown to signed-in users when
    they are signed in, or a public one (to signed-in users only while ``ALLOW_PUBLIC_ACCESS``
    is off). Anyone else is a 404.
    """
    user = get_object_or_404(User, username=username)
    if not can_see_profile(request.user, user):
        raise Http404
    return user


class PublicUserListView(APIView):
    openapi_tags = ['Users']
    permission_classes = [AllowAny]

    @extend_schema(responses=PublicProfileSerializer(many=True))
    def get(self, request):
        """
        List profiles

        Everyone whose profile you may see, except you: public profiles, and to signed-in users
        also the profiles shown to signed-in users.
        """
        users = User.objects.filter(visible_profiles_q(request.user))
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
        # visibility is public (or signed-in, for signed-in viewers), and as a card: the
        # private plan is not part of a profile.
        locations = Location.objects.filter(user=user, is_public=True)
        shown = [Collection.Visibility.PUBLIC]
        if request.user.is_authenticated:
            shown.append(Collection.Visibility.SIGNED_IN)
        collections = Collection.objects.filter(user=user, visibility__in=shown)
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
