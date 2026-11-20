"""Public profiles: who can be found, and what is shown about them."""

from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef, Prefetch
from django.http import Http404
from django.utils import timezone
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from adventures.models import Collection, ContentImage, Location, Visit
from adventures.serializers import LocationListSerializer, LocationSerializer, UltraSlimCollectionSerializer
from adventures.views.mixins import PaginatedResponseMixin
from adventures.services.user_stats import UserStatsService
from core.pagination import StandardResultsSetPagination
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


def _shown_locations(user):
    """A location is listed on a profile by its own flag."""
    return Location.objects.filter(user=user, is_public=True)


def _shown_collections(request, user):
    """
    A collection is listed only when its visibility is public (or signed-in, for signed-in
    viewers), and as a card: the private plan is not part of a profile.
    """
    shown = [Collection.Visibility.PUBLIC]
    if request.user.is_authenticated:
        shown.append(Collection.Visibility.SIGNED_IN)
    return Collection.objects.filter(user=user, visibility__in=shown)


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
        404 to everyone but their owner. Pass `locations=false` to leave the locations out
        (they are listed a page at a time by `/users/{username}/locations/`).
        """
        user = _visible_user(request, username)
        payload = {
            'user': PublicProfileSerializer(user).data,
            'collections': UltraSlimCollectionSerializer(
                _shown_collections(request, user), many=True, context={'request': request}
            ).data,
        }
        if request.query_params.get('locations', 'true').lower() not in ('false', '0'):
            payload['locations'] = LocationSerializer(
                _shown_locations(user), many=True, context={'request': request}
            ).data
        return Response(payload)


class PublicUserLocationsView(APIView, PaginatedResponseMixin):
    openapi_tags = ['Users']
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    ORDERINGS = {
        'recent': '-updated_at',
        'oldest': 'created_at',
        'name': 'name',
        'rating': '-rating',
    }

    def get_serializer_context(self):
        return {'request': self.request, 'view': self}

    @extend_schema(
        parameters=[
            OpenApiParameter('ordering', str, enum=list(ORDERINGS), description='`recent` by default.'),
            OpenApiParameter('category', str, description='A category name.'),
        ],
        responses=LocationListSerializer(many=True),
    )
    def get(self, request, username):
        """
        List a user's public locations

        Their public locations a page at a time, in the light form the location lists use.
        """
        user = _visible_user(request, username)
        now = timezone.now()
        queryset = (
            _shown_locations(user)
            .annotate(annotated_is_visited=Exists(Visit.objects.filter(location_id=OuterRef('pk'), start_date__lte=now)))
            .select_related('category', 'user')
            .prefetch_related(Prefetch('images', queryset=ContentImage.objects.select_related('user')), 'collections')
        )
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__name=category)
        ordering = self.ORDERINGS.get(request.query_params.get('ordering'), self.ORDERINGS['recent'])
        # `id` keeps pages stable when the ordering key ties.
        return self.paginate_and_respond(
            queryset.order_by(ordering, 'id'), request, serializer_class=LocationListSerializer
        )


class PublicUserPinsView(APIView):
    openapi_tags = ['Users']
    permission_classes = [AllowAny]

    @extend_schema(
        responses=inline_serializer(
            'PublicProfilePin',
            many=True,
            fields={
                'id': serializers.UUIDField(),
                'name': serializers.CharField(),
                'latitude': serializers.FloatField(),
                'longitude': serializers.FloatField(),
                'category': serializers.CharField(allow_null=True, help_text='The category icon.'),
                'category_name': serializers.CharField(allow_null=True, help_text='The category name.'),
                'is_visited': serializers.BooleanField(),
            },
        )
    )
    def get(self, request, username):
        """
        List a user's map pins

        Every public location that has coordinates, with just what a map needs.
        """
        user = _visible_user(request, username)
        now = timezone.now()
        rows = (
            _shown_locations(user)
            .exclude(coordinates__isnull=True)
            .annotate(is_visited=Exists(Visit.objects.filter(location_id=OuterRef('pk'), start_date__lte=now)))
            .values('id', 'name', 'coordinates', 'category__icon', 'category__display_name', 'is_visited')
        )
        return Response([
            {
                'id': row['id'],
                'name': row['name'],
                # A point is (x, y) = (longitude, latitude).
                'latitude': row['coordinates'].y,
                'longitude': row['coordinates'].x,
                'category': row['category__icon'],
                'category_name': row['category__display_name'],
                'is_visited': row['is_visited'],
            }
            for row in rows
        ])


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
        stats = _stats_service.build_user_stats(user, request.user, include_categories=True)
        if not (request.user.is_authenticated and request.user.pk == user.pk):
            # Other people see what the profile lists, not how much is kept private.
            stats['location_count'] = _shown_locations(user).count()
            stats['trips_count'] = _shown_collections(request, user).count()
        return Response(stats)


__all__ = [
    'PublicUserDetailView',
    'PublicUserListView',
    'PublicUserLocationsView',
    'PublicUserPinsView',
    'PublicUserStatsView',
]
