"""Itinerary days and the items placed on them."""

from adventures.models import CollectionItineraryItem, CollectionItineraryDay, Lodging, Transportation
from rest_framework import serializers
from core.serializers import CustomModelSerializer
from adventures.services import day_plan
from .logistics import LodgingSerializer, TransportationSerializer

class CollectionItineraryDaySerializer(CustomModelSerializer):
    class Meta:
        model = CollectionItineraryDay
        fields = ['id', 'collection', 'index', 'date', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'index', 'created_at', 'updated_at']
        # The (collection, date) constraint only applies to date-keyed rows.
        validators = []

    def validate(self, attrs):
        data = super().validate(attrs)
        if self.instance is None:
            collection = data.get('collection')
            if collection is not None and day_plan.is_day_based(collection):
                raise serializers.ValidationError({
                    'collection': 'Add days to a day-based trip with the itinerary day actions.'
                })
            if not data.get('date'):
                raise serializers.ValidationError({'date': 'A date is required.'})
            if collection is not None and CollectionItineraryDay.objects.filter(
                collection=collection, index__isnull=True, date=data['date']
            ).exists():
                raise serializers.ValidationError({'date': 'This date already has day details.'})
        return data
    
    def update(self, instance, validated_data):
        # Security: Prevent changing collection or date after creation
        # This prevents shared users from reassigning itinerary days to themselves
        validated_data.pop('collection', None)
        validated_data.pop('date', None)
        return super().update(instance, validated_data)


class CollectionItineraryItemSerializer(CustomModelSerializer):
    date = serializers.DateField(required=False, allow_null=True, default=None)
    item = serializers.SerializerMethodField()
    start_datetime = serializers.ReadOnlyField()
    end_datetime = serializers.ReadOnlyField()
    object_name = serializers.ReadOnlyField(source='content_type.model')
    is_global = serializers.BooleanField(required=False, default=False)
    day_index = serializers.SerializerMethodField()
    
    class Meta:
        model = CollectionItineraryItem
        fields = [
            'id', 'collection', 'content_type', 'object_id', 'item', 'date', 'is_global', 'order',
            'day', 'day_index', 'span_end_index', 'is_optional', 'start_time', 'end_time', 'timezone',
            'logged_visit', 'start_datetime', 'end_datetime', 'created_at', 'updated_at', 'object_name',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'start_datetime', 'end_datetime', 'item', 'object_name',
            'day', 'day_index', 'span_end_index', 'logged_visit',
        ]
        # DRF 3.15 generates UniqueTogetherValidator from UniqueConstraints without applying
        # their conditions, causing false 400s (e.g. a dated item with order=0 is rejected
        # when a global item with the same order exists). The view and DB constraints
        # already enforce the correct conditional uniqueness.
        validators = []

    def validate(self, attrs):
        data = super().validate(attrs)

        is_global = data.get('is_global')
        if is_global is None and self.instance is not None:
            is_global = self.instance.is_global

        if 'date' in data:
            date = data.get('date')
        elif self.instance is not None:
            date = self.instance.date
        else:
            date = None

        if is_global and date is not None:
            raise serializers.ValidationError({
                'date': 'Global items must not have a date.',
                'is_global': 'Provide either a date or set is_global, not both.',
            })

        collection = data.get('collection') or getattr(self.instance, 'collection', None)
        if (
            not is_global
            and date is None
            and self.instance is None
            and not (collection is not None and day_plan.is_day_based(collection))
        ):
            raise serializers.ValidationError({
                'date': 'Dated items must include a date. To create a trip-wide item, set is_global=true.',
            })

        return data

    def get_day_index(self, obj):
        return obj.day.index if obj.day_id else None
    
    def update(self, instance, validated_data):
        # Security: Prevent changing collection, content_type, or object_id after creation
        # This prevents shared users from reassigning itinerary items to themselves
        # or linking items to objects they don't have permission to access
        validated_data.pop('collection', None)
        validated_data.pop('content_type', None)
        validated_data.pop('object_id', None)
        return super().update(instance, validated_data)
    
    def get_item(self, obj):
        """Return id and type for the linked item"""
        if not obj.item:
            return None
            
        return {
            'id': str(obj.item.id),
            'type': obj.content_type.model,
        }

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Frontend resolves itinerary rows by model name (`location`, `lodging`, ...),
        # while DRF would otherwise emit the ContentType primary key.
        representation['content_type'] = instance.content_type.model if instance.content_type_id else None
        representation['object_id'] = str(instance.object_id)
        representation['collection'] = str(instance.collection_id)
        representation['day'] = str(instance.day_id) if instance.day_id else None
        representation['logged_visit'] = str(instance.logged_visit_id) if instance.logged_visit_id else None
        return representation


def plan_state(collection, context=None):
    """The day plan the planner renders, returned after structural changes."""
    from adventures.services.day_plan.files import serialize_day_files

    collection.refresh_from_db()
    items = (
        CollectionItineraryItem.objects.filter(collection=collection)
        .select_related('day', 'content_type')
        .prefetch_related('item')
    )
    days = CollectionItineraryDay.objects.filter(collection=collection).order_by('index', 'date')
    context = context or {}
    state = {
        'collection': {
            'id': str(collection.id),
            'start_date': collection.start_date,
            'end_date': collection.end_date,
            'timezone': collection.timezone,
            'day_count': day_plan.day_count(collection) or None,
            'updated_at': collection.updated_at,
        },
        'itinerary': CollectionItineraryItemSerializer(items, many=True, context=context).data,
        'itinerary_days': CollectionItineraryDaySerializer(days, many=True, context=context).data,
        'lodging': LodgingSerializer(collection.lodging_set.all(), many=True, context=context).data,
        'transportations': TransportationSerializer(collection.transportation_set.all(), many=True, context=context).data,
    }
    state.update(serialize_day_files(collection, context))
    return state


def serialize_updated_object(obj, context):
    if obj is None:
        return None
    if isinstance(obj, Lodging):
        return LodgingSerializer(obj, context=context).data
    if isinstance(obj, Transportation):
        return TransportationSerializer(obj, context=context).data
    return None


def add_quick_add_extras(response_data, itinerary_item, image_import_summary):
    """Add the placement and any failed photos to a quick add response."""
    if itinerary_item:
        response_data['quick_add_itinerary_item'] = CollectionItineraryItemSerializer(itinerary_item).data
    if image_import_summary and image_import_summary.get('failed'):
        response_data['quick_add_image_import'] = {
            'created_count': image_import_summary['created_count'],
            'failed_count': image_import_summary['failed_count'],
            'failed': image_import_summary['failed'],
        }
    return response_data
