"""Trails, activities, and visits."""

import logging
from adventures.models import Visit, Trail, Activity
from rest_framework import serializers
from core.serializers import CustomModelSerializer
from core.public_url import build_media_url
from adventures.utils.geojson import cached_gpx_geojson
from core.dates import ensure_aware_utc, normalize_all_day_visit_dates
from adventures.serializers.geo_fields import ActivityCoordinateMixin
from integrations.facade import (
    build_wanderer_trail_view_url,
    extract_wanderer_author_from_trail,
    fetch_trail_by_id,
    fetch_trail_geojson,
    wanderer_integration_for,
)

logger = logging.getLogger(__name__)


class TrailSerializer(CustomModelSerializer):
    provider = serializers.SerializerMethodField()
    wanderer_data = serializers.SerializerMethodField()
    wanderer_link = serializers.SerializerMethodField()
    geojson = serializers.SerializerMethodField(read_only=True)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._wanderer_integration_cache = {}
    
    class Meta:
        model = Trail
        fields = [
            'id', 'user', 'name', 'location', 'day', 'collection', 'span_end_index', 'day_index',
            'created_at', 'link',
            'wanderer_id', 'wanderer_author_username', 'wanderer_author_domain',
            'provider', 'wanderer_data', 'wanderer_link', 'geojson',
        ]
        read_only_fields = ['id', 'created_at', 'user', 'provider', 'wanderer_link', 'day_index']

    day_index = serializers.SerializerMethodField()

    def get_day_index(self, obj):
        return obj.day.index if obj.day_id else None

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        location = attrs.get('location', getattr(instance, 'location', None) if instance else None)
        day = attrs.get('day', getattr(instance, 'day', None) if instance else None)
        collection = attrs.get('collection', getattr(instance, 'collection', None) if instance else None)
        if sum(parent is not None for parent in (location, day, collection)) != 1:
            raise serializers.ValidationError(
                'A trail belongs to a location, a trip day, or Ideas.'
            )
        span = attrs.get('span_end_index', getattr(instance, 'span_end_index', None) if instance else None)
        if span is not None and day is None:
            raise serializers.ValidationError({'span_end_index': 'Only a trail on a day can span days.'})
        if span is not None and day is not None and span < day.index:
            raise serializers.ValidationError({'span_end_index': 'A span cannot end before it starts.'})
        return attrs

    def _get_wanderer_integration(self, user):
        """Cache wanderer integration to avoid multiple database queries"""
        if user.id not in self._wanderer_integration_cache:
            self._wanderer_integration_cache[user.id] = wanderer_integration_for(user)
        return self._wanderer_integration_cache[user.id]

    def _ensure_wanderer_author_fields(self, obj, integration, trail_data=None):
        """Backfill username/domain from Wanderer API when missing on existing trails."""
        if not obj.wanderer_id or not integration:
            return obj.wanderer_author_username, obj.wanderer_author_domain

        username = (obj.wanderer_author_username or '').strip() or None
        domain = (obj.wanderer_author_domain or '').strip() or None
        if username and domain:
            return username, domain


        if trail_data is None:
            try:
                trail_data = fetch_trail_by_id(integration, obj.wanderer_id)
            except Exception as exc:
                logger.warning(
                    "Could not fetch Wanderer trail %s for author backfill: %s",
                    obj.wanderer_id,
                    exc,
                )
                return username, domain

        resolved_username, resolved_domain = extract_wanderer_author_from_trail(trail_data)
        username = username or resolved_username
        domain = domain or resolved_domain

        updates = {}
        if username and username != obj.wanderer_author_username:
            updates['wanderer_author_username'] = username
            obj.wanderer_author_username = username
        if domain and domain != obj.wanderer_author_domain:
            updates['wanderer_author_domain'] = domain
            obj.wanderer_author_domain = domain
        if updates:
            Trail.objects.filter(pk=obj.pk).update(**updates)

        return username, domain

    def _build_wanderer_link(self, obj, integration, trail_data=None):
        if not obj.wanderer_id or not integration:
            return None


        username, domain = self._ensure_wanderer_author_fields(
            obj, integration, trail_data=trail_data
        )
        if not username or not domain:
            return None

        try:
            return build_wanderer_trail_view_url(
                integration.server_url,
                obj.wanderer_id,
                username,
                domain,
            )
        except Exception as exc:
            logger.warning(
                "Could not build Wanderer link for trail %s: %s",
                obj.wanderer_id,
                exc,
            )
            return None

    def get_provider(self, obj):
        if obj.wanderer_id:
            return 'Wanderer'
        # check the link to get the provider such as Strava, AllTrails, etc.
        if obj.link:
            if 'strava' in obj.link:
                return 'Strava'
            elif 'alltrails' in obj.link:
                return 'AllTrails'
            elif 'komoot' in obj.link:
                return 'Komoot'
            elif 'outdooractive' in obj.link:
                return 'Outdooractive'
        return 'External Link'
    
    def get_wanderer_data(self, obj):
        # The published story shows a trail's name and link, never Wanderer's own data.
        if not obj.wanderer_id or self.context.get('story'):
            return None

        integration = self._get_wanderer_integration(obj.user)
        if not integration:
            return None

        if hasattr(obj, '_wanderer_data'):
            return obj._wanderer_data


        try:
            trail_data = fetch_trail_by_id(integration, obj.wanderer_id)
            if not trail_data:
                return None
            obj._wanderer_data = trail_data
            self._ensure_wanderer_author_fields(obj, integration, trail_data=trail_data)
            obj._wanderer_link = self._build_wanderer_link(
                obj, integration, trail_data=trail_data
            )
            return trail_data
        except Exception as e:
            logger.error("Error fetching Wanderer trail data for %s: %s", obj.wanderer_id, e)
            return None

    def get_wanderer_link(self, obj):
        if not obj.wanderer_id:
            return None

        integration = self._get_wanderer_integration(obj.user)
        if not integration:
            return None

        if hasattr(obj, '_wanderer_link') and obj._wanderer_link:
            return obj._wanderer_link

        return self._build_wanderer_link(obj, integration)

    def get_geojson(self, obj):
        if not obj.wanderer_id or self.context.get('story'):
            return None

        integration = self._get_wanderer_integration(obj.user)
        if not integration:
            return None


        trail_data = getattr(obj, '_wanderer_data', None)
        try:
            return fetch_trail_geojson(
                integration,
                obj.wanderer_id,
                trail_data=trail_data,
            )
        except Exception as exc:
            logger.warning(
                "Could not fetch GeoJSON for Wanderer trail %s: %s",
                obj.wanderer_id,
                exc,
            )
            return None

    def _sync_wanderer_author_fields(self, validated_data, user):
        wanderer_id = validated_data.get('wanderer_id')
        if wanderer_id is None:
            return validated_data
        if not wanderer_id:
            validated_data['wanderer_author_username'] = None
            validated_data['wanderer_author_domain'] = None
            return validated_data

        username = (validated_data.get('wanderer_author_username') or '').strip() or None
        domain = (validated_data.get('wanderer_author_domain') or '').strip().lstrip('@') or None

        if username and domain:
            validated_data['wanderer_author_username'] = username
            validated_data['wanderer_author_domain'] = domain
            return validated_data

        integration = self._get_wanderer_integration(user)
        if not integration:
            return validated_data


        try:
            trail_data = fetch_trail_by_id(integration, wanderer_id)
            resolved_username, resolved_domain = extract_wanderer_author_from_trail(trail_data)
            if resolved_username:
                validated_data['wanderer_author_username'] = resolved_username
            if resolved_domain:
                validated_data['wanderer_author_domain'] = resolved_domain
        except Exception as exc:
            logger.warning(
                "Could not resolve Wanderer author for trail %s: %s",
                wanderer_id,
                exc,
            )

        return validated_data

    def create(self, validated_data):
        user = validated_data.get('user')
        if user:
            validated_data = self._sync_wanderer_author_fields(validated_data, user)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'wanderer_id' in validated_data or (
            'wanderer_author_username' in validated_data
            or 'wanderer_author_domain' in validated_data
        ):
            merged = {
                'wanderer_id': validated_data.get('wanderer_id', instance.wanderer_id),
                'wanderer_author_username': validated_data.get(
                    'wanderer_author_username',
                    instance.wanderer_author_username,
                ),
                'wanderer_author_domain': validated_data.get(
                    'wanderer_author_domain',
                    instance.wanderer_author_domain,
                ),
            }
            merged = self._sync_wanderer_author_fields(merged, instance.user)
            validated_data['wanderer_author_username'] = merged.get('wanderer_author_username')
            validated_data['wanderer_author_domain'] = merged.get('wanderer_author_domain')
        return super().update(instance, validated_data)


class ActivitySerializer(ActivityCoordinateMixin, CustomModelSerializer):
    geojson = serializers.SerializerMethodField()
    day_index = serializers.SerializerMethodField()
    promoted_visit = serializers.SerializerMethodField()
    promoted_location = serializers.SerializerMethodField()
    
    class Meta:
        model = Activity
        fields = [
            'id', 'user', 'visit', 'day', 'collection', 'trail', 'gpx_file', 'name', 'sport_type',
            'distance', 'moving_time', 'elapsed_time', 'rest_time', 'elevation_gain',
            'elevation_loss', 'elev_high', 'elev_low', 'start_date', 'start_date_local',
            'timezone', 'average_speed', 'max_speed', 'average_cadence', 'calories',
            'start_lat', 'start_lng', 'end_lat', 'end_lng', 'external_service_id', 'geojson',
            'day_index', 'promoted_activity', 'promoted_visit', 'promoted_location',
        ]
        read_only_fields = ['id', 'user', 'promoted_activity', 'day_index', 'promoted_visit', 'promoted_location']

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        visit = attrs.get('visit', getattr(instance, 'visit', None) if instance else None)
        day = attrs.get('day', getattr(instance, 'day', None) if instance else None)
        collection = attrs.get('collection', getattr(instance, 'collection', None) if instance else None)
        if sum(parent is not None for parent in (visit, day, collection)) != 1:
            raise serializers.ValidationError(
                'An activity belongs to a visit, a trip day, or Ideas.'
            )
        return attrs

    def get_day_index(self, obj):
        return obj.day.index if obj.day_id else None

    def get_promoted_visit(self, obj):
        copy = obj.promoted_activity if obj.promoted_activity_id else None
        if copy is None or not copy.visit_id:
            return None
        return str(copy.visit_id)

    def get_promoted_location(self, obj):
        copy = obj.promoted_activity if obj.promoted_activity_id else None
        if copy is None or not copy.visit_id or not copy.visit.location_id:
            return None
        return str(copy.visit.location_id)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.gpx_file:
            representation['gpx_file'] = build_media_url(instance.gpx_file.name)
        return representation
    
    def get_geojson(self, obj):
        # In the story, tracks are shown only when the owner turned the GPX group on.
        if self.context.get('story') and not self.context.get('story_gpx'):
            return None
        return cached_gpx_geojson(obj.gpx_file)


class VisitSerializer(serializers.ModelSerializer):

    activities = ActivitySerializer(many=True, read_only=True, required=False)

    class Meta:
        model = Visit
        fields = ['id', 'start_date', 'end_date', 'timezone', 'notes', 'activities','location', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        for field in ('start_date', 'end_date'):
            if field in attrs and attrs[field] is not None:
                attrs[field] = ensure_aware_utc(attrs[field])

        instance = getattr(self, 'instance', None)
        start = attrs.get('start_date', getattr(instance, 'start_date', None) if instance else None)
        end = attrs.get('end_date', getattr(instance, 'end_date', None) if instance else None)

        if start is not None:
            normalized_start, normalized_end = normalize_all_day_visit_dates(start, end)
            attrs['start_date'] = normalized_start
            if normalized_end is not None:
                attrs['end_date'] = normalized_end

        return attrs

    def create(self, validated_data):
        if not validated_data.get('end_date') and validated_data.get('start_date'):
            validated_data['end_date'] = validated_data['start_date']
        return super().create(validated_data)


class LocationVisitSerializer(VisitSerializer):
    """
    A visit as sent inside a location. The optional ``id`` says which of the location's
    existing visits this is, so saving a place keeps those visits (and their activities)
    instead of recreating them.
    """

    id = serializers.UUIDField(required=False)

    class Meta(VisitSerializer.Meta):
        read_only_fields = ['created_at', 'updated_at']
