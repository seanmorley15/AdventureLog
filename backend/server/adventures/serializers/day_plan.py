"""Requests and responses of the day plan: days, itinerary items, and plan-wide changes."""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from adventures.services.day_plan import DayPlanError, parse_day_date

from .activity import ActivitySerializer, TrailSerializer, VisitSerializer
from .itinerary import CollectionItineraryDaySerializer, CollectionItineraryItemSerializer
from .logistics import LodgingSerializer, TransportationSerializer

@extend_schema_field(OpenApiTypes.DATE)
class DayDateField(serializers.Field):
    """A calendar day, read the way the day plan reads dates (a date-time keeps its date)."""

    def to_internal_value(self, data):
        try:
            return parse_day_date(data)
        except DayPlanError as exc:
            raise serializers.ValidationError(exc.message)

    def to_representation(self, value):
        return value.isoformat() if value else None


ITEM_CONTENT_TYPES = ['location', 'lodging', 'transportation', 'note', 'checklist', 'visit']
DESTINATIONS = ['day', 'ideas']


class _PlacementFields(serializers.Serializer):
    day_index = serializers.IntegerField(
        required=False, allow_null=True, min_value=1,
        help_text='Day-based trips: the day (1 = first). Omit or null for Ideas.',
    )
    is_global = serializers.BooleanField(required=False, help_text='Trip-wide (not on one day).')
    order = serializers.IntegerField(required=False, allow_null=True, min_value=0, help_text='Position on the day.')
    span_end_index = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, help_text='For a stay or journey over several days: the last day.'
    )
    is_optional = serializers.BooleanField(required=False)
    start_time = serializers.TimeField(required=False, allow_null=True)
    end_time = serializers.TimeField(required=False, allow_null=True)
    timezone = serializers.CharField(required=False, allow_null=True, allow_blank=True, help_text='IANA name.')
    date = serializers.DateField(
        required=False, allow_null=True,
        help_text='Trips keyed by date: the day. Day-based trips accept it instead of `day_index`.',
    )


class ItineraryItemCreateSerializer(_PlacementFields):
    content_type = serializers.ChoiceField(
        choices=ITEM_CONTENT_TYPES, help_text='The kind of record to place. A `visit` places its location.'
    )
    object_id = serializers.UUIDField()


class ItineraryItemUpdateSerializer(_PlacementFields):
    """Moving fields (`day_index`, `is_global`, `order`, `span_end_index`) move the item."""


class ItineraryItemResultSerializer(CollectionItineraryItemSerializer):
    # Not read_only: drf-spectacular marks read-only fields as always present.
    updated_object = serializers.DictField(
        required=False,
        help_text='The lodging or transportation, when placing it changed its dates.',
    )

    class Meta(CollectionItineraryItemSerializer.Meta):
        fields = [*CollectionItineraryItemSerializer.Meta.fields, 'updated_object']


class ItemDeleteQuerySerializer(serializers.Serializer):
    confirm_delete_visits = serializers.BooleanField(
        default=False, help_text='Also delete the visit this item logged.'
    )


class ReorderEntrySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    order = serializers.IntegerField(min_value=0)
    day_index = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    date = serializers.DateField(required=False, allow_null=True)
    is_global = serializers.BooleanField(required=False, default=False)
    span_end_index = serializers.IntegerField(required=False, allow_null=True, min_value=1)


class ReorderSerializer(serializers.Serializer):
    items = ReorderEntrySerializer(many=True, help_text='Every item whose place changed, with its new place.')


class ReorderResultSerializer(serializers.Serializer):
    items = CollectionItineraryItemSerializer(many=True)
    updated_objects = serializers.ListField(
        child=serializers.DictField(), help_text='Lodging and transportation whose dates moved with them.'
    )


class LogVisitSerializer(serializers.Serializer):
    date = DayDateField(required=False, allow_null=True, help_text='Needed when the trip has no dates.')


class LogItemResultSerializer(serializers.Serializer):
    item = CollectionItineraryItemSerializer()
    visit = VisitSerializer()
    created = serializers.BooleanField(help_text='False when the stop had already logged this visit.')


class LogDayResultSerializer(serializers.Serializer):
    items = CollectionItineraryItemSerializer(many=True, help_text='The stops that were logged.')
    visits = VisitSerializer(many=True)
    activities_need_stop = serializers.ListField(
        child=serializers.UUIDField(), help_text='Day activities to log by hand: the day has several stops.'
    )
    day_activities = ActivitySerializer(many=True)
    day_trails = TrailSerializer(many=True)
    day_images = serializers.ListField(child=serializers.DictField())


class DayInsertSerializer(serializers.Serializer):
    position = serializers.IntegerField(required=False, allow_null=True, min_value=1, help_text='Becomes this day. Default: last.')
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class DayMoveSerializer(serializers.Serializer):
    position = serializers.IntegerField(min_value=1)


class DayDeleteQuerySerializer(serializers.Serializer):
    destination = serializers.ChoiceField(
        choices=DESTINATIONS, required=False,
        help_text='Where the stops on the day go: another `day` (with `target_day`) or `ideas`. '
        'Needed when the day has stops (`400 destination_required`).',
    )
    target_day = serializers.UUIDField(required=False)


class PlanByDaysSerializer(serializers.Serializer):
    day_count = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, help_text='Default: the number of days between the dates.'
    )


class DurationSerializer(serializers.Serializer):
    day_count = serializers.IntegerField(min_value=1)
    start_date = DayDateField(
        required=False, allow_null=True, help_text='Set or move the first day; null makes the trip undated.'
    )
    end_date = DayDateField(
        required=False, allow_null=True, help_text='Optional check: must match `start_date` + `day_count` − 1.'
    )
    destination = serializers.ChoiceField(choices=DESTINATIONS, required=False)
    target_day = serializers.UUIDField(required=False)
    timezone = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ShiftSerializer(serializers.Serializer):
    days = serializers.IntegerField(required=False, help_text='Move the whole trip by this many days (may be negative).')
    start_date = DayDateField(required=False, help_text='Or move it to start on this date.')

    def validate(self, attrs):
        if attrs.get('days') is None and attrs.get('start_date') is None:
            raise serializers.ValidationError('Send days or start_date.')
        return attrs


class _PlanCollectionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    start_date = serializers.DateField(allow_null=True)
    end_date = serializers.DateField(allow_null=True)
    timezone = serializers.CharField(allow_null=True)
    day_count = serializers.IntegerField(allow_null=True)
    updated_at = serializers.DateTimeField()


class PlanStateSerializer(serializers.Serializer):
    collection = _PlanCollectionSerializer()
    itinerary = CollectionItineraryItemSerializer(many=True)
    itinerary_days = CollectionItineraryDaySerializer(many=True)
    lodging = LodgingSerializer(many=True)
    transportations = TransportationSerializer(many=True)
    day_activities = ActivitySerializer(many=True)
    day_trails = TrailSerializer(many=True)
    day_images = serializers.ListField(child=serializers.DictField())


class PlanStateWithDaySerializer(PlanStateSerializer):
    day = serializers.UUIDField(help_text='The new day.')


class AutoGenerateResultSerializer(serializers.Serializer):
    items = CollectionItineraryItemSerializer(many=True)
