from datetime import date, timedelta

from django.db.models import Prefetch, Q

from adventures.models import Collection, CollectionInvite, ContentImage, Location
from adventures.serializers import LocationSerializer, UltraSlimCollectionSerializer
from adventures.services.calendar_events import get_calendar_events_for_user
from adventures.services.user_stats import UserStatsService

MAX_RECENT_LOCATIONS = 3
MAX_UPCOMING_TRIPS = 3
MAX_UPCOMING_EVENTS = 10


def _collection_list_queryset(user):
    return (
        Collection.objects.filter(Q(user=user.id) & Q(is_archived=False))
        .distinct()
        .select_related('user', 'primary_image')
        .prefetch_related(
            Prefetch(
                'locations__images',
                queryset=ContentImage.objects.filter(is_primary=True).select_related('user'),
                to_attr='primary_images',
            ),
            'shared_with',
        )
    )


def _serialize_collections(collections, request):
    serializer = UltraSlimCollectionSerializer(
        collections,
        many=True,
        context={'request': request},
    )
    return serializer.data


def build_dashboard_data(user, request_user, *, events_days=30, request=None):
    stats_service = UserStatsService()
    stats = stats_service.build_user_stats(user, request_user, include_categories=False)

    today = date.today()
    end_date = today + timedelta(days=events_days)

    recent_locations_qs = (
        Location.objects.filter(user=user)
        .filter(visits__start_date__lte=today)
        .distinct()
        .select_related('category', 'country', 'region', 'city', 'user')
        .prefetch_related('visits', 'images', 'attachments', 'collections', 'trails')
        .order_by('-updated_at')[:MAX_RECENT_LOCATIONS]
    )
    recent_locations = LocationSerializer(
        recent_locations_qs,
        many=True,
        context={'request': request},
    ).data

    collections_qs = _collection_list_queryset(user)

    upcoming_trips_qs = (
        collections_qs.filter(start_date__gt=today).order_by('start_date')[:MAX_UPCOMING_TRIPS]
    )
    upcoming_trips = _serialize_collections(upcoming_trips_qs, request)

    active_trip_obj = (
        collections_qs.filter(start_date__lte=today, end_date__gte=today).order_by('start_date').first()
    )
    active_trip = (
        _serialize_collections([active_trip_obj], request)[0] if active_trip_obj else None
    )

    upcoming_events = get_calendar_events_for_user(
        user,
        start=today.isoformat(),
        end=end_date.isoformat(),
    )
    upcoming_events = upcoming_events[:MAX_UPCOMING_EVENTS]

    invite_count = CollectionInvite.objects.filter(invited_user=user).count()

    return {
        'stats': stats,
        'recent_locations': recent_locations,
        'upcoming_trips': upcoming_trips,
        'active_trip': active_trip,
        'upcoming_events': upcoming_events,
        'invite_count': invite_count,
    }
