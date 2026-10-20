"""Transportation, lodging, notes, and checklists."""

import logging
import gpxpy
from adventures.models import ChecklistItem, Note, Transportation, Checklist, Lodging
from rest_framework import serializers
from core.serializers import CustomModelSerializer
from geopy.distance import geodesic
from adventures.utils.geojson import cached_gpx_distance_km
from core.geo import point_to_lat_lon
from adventures.serializers.geo_fields import CoordinateSerializerMixin, TransportationCoordinateMixin
from .media import MediaFieldsMixin

logger = logging.getLogger(__name__)


class TransportationSerializer(MediaFieldsMixin, TransportationCoordinateMixin, CustomModelSerializer):
    distance = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    travel_duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Transportation
        fields = [
            'id', 'user', 'type', 'name', 'description', 'rating', 'price', 'price_currency',
            'link', 'date', 'flight_number', 'from_location', 'to_location', 
            'is_public', 'collection', 'created_at', 'updated_at', 'end_date',
            'origin_latitude', 'origin_longitude', 'destination_latitude', 'destination_longitude',
            'start_timezone', 'end_timezone', 'distance', 'images', 'attachments', 'start_code', 'end_code',
            'travel_duration_minutes'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'distance', 'travel_duration_minutes']

    def get_distance(self, obj):
        gpx_distance = self._get_gpx_distance_km(obj)
        if gpx_distance is not None:
            return gpx_distance

        o_lat, o_lon = point_to_lat_lon(obj.origin)
        d_lat, d_lon = point_to_lat_lon(obj.destination)
        if o_lat is not None and o_lon is not None and d_lat is not None and d_lon is not None:
            try:
                origin = (o_lat, o_lon)
                destination = (d_lat, d_lon)
                return round(geodesic(origin, destination).km, 2)
            except ValueError:
                return None
        return None

    def _get_gpx_distance_km(self, obj):
        # Filter in Python so a prefetched attachment list is reused instead of queried again.
        for attachment in obj.attachments.all():
            if not attachment.file or not attachment.file.name.lower().endswith('.gpx'):
                continue
            distance_km = cached_gpx_distance_km(attachment.file, self._parse_gpx_distance_km)
            if distance_km is not None:
                return distance_km
        return None

    def _parse_gpx_distance_km(self, gpx_file_field):
        try:
            with gpx_file_field.open('r') as gpx_file:
                gpx = gpxpy.parse(gpx_file)

            total_meters = 0.0

            for track in gpx.tracks:
                for segment in track.segments:
                    segment_length = segment.length_3d() or segment.length_2d()
                    if segment_length:
                        total_meters += segment_length

            for route in gpx.routes:
                route_length = route.length_3d() or route.length_2d()
                if route_length:
                    total_meters += route_length

            if total_meters > 0:
                return round(total_meters / 1000, 2)
        except Exception as exc:
            logger.warning(
                "Failed to calculate GPX distance for file %s: %s",
                getattr(gpx_file_field, 'name', 'unknown'),
                exc,
            )
        return None

    def get_travel_duration_minutes(self, obj):
        if not obj.date or not obj.end_date:
            return None

        if self._is_all_day(obj.date) and self._is_all_day(obj.end_date):
            return None

        try:
            total_minutes = int((obj.end_date - obj.date).total_seconds() // 60)
            return total_minutes if total_minutes >= 0 else None
        except Exception:
            logger.warning(
                "Failed to calculate travel duration for transportation %s",
                getattr(obj, "id", "unknown"),
                exc_info=True,
            )
            return None

    def _is_all_day(self, dt_value):
        return (
            dt_value.time().hour == 0
            and dt_value.time().minute == 0
            and dt_value.time().second == 0
            and dt_value.time().microsecond == 0
        )


class LodgingSerializer(MediaFieldsMixin, CoordinateSerializerMixin, CustomModelSerializer):
    images = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = Lodging
        fields = [
            'id', 'user', 'name', 'description', 'rating', 'link', 'check_in', 'check_out', 
            'reservation_number', 'price', 'price_currency', 'latitude', 'longitude', 'location', 'is_public',
            'collection', 'created_at', 'updated_at', 'type', 'timezone', 'images', 'attachments'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']


class NoteSerializer(CustomModelSerializer):

    class Meta:
        model = Note
        fields = [
            'id', 'user', 'name', 'content', 'date', 'links', 
            'is_public', 'is_private', 'collection', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']


class ChecklistItemSerializer(CustomModelSerializer):
        class Meta:
            model = ChecklistItem
            fields = [
                'id', 'user', 'name', 'is_checked', 'is_private', 'checklist', 'created_at', 'updated_at'
            ]
            read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'checklist']


class ChecklistSerializer(CustomModelSerializer):
    items = ChecklistItemSerializer(many=True, source='checklistitem_set')
    
    class Meta:
        model = Checklist
        fields = [
            'id', 'user', 'name', 'date', 'is_public', 'collection', 'created_at', 'updated_at', 'items'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']
    
    def create(self, validated_data):
        items_data = validated_data.pop('checklistitem_set')
        checklist = Checklist.objects.create(**validated_data)
        
        for item_data in items_data:
            # Remove user from item_data to avoid constraint issues
            item_data.pop('user', None)
            # Set user from the parent checklist
            ChecklistItem.objects.create(
                checklist=checklist, 
                user=checklist.user,
                **item_data
            )
        return checklist
    
    def update(self, instance, validated_data):
        items_data = validated_data.pop('checklistitem_set', [])
        
        # Update Checklist fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Get current items
        current_items = instance.checklistitem_set.all()
        current_item_ids = set(current_items.values_list('id', flat=True))
        
        # Update or create items
        updated_item_ids = set()
        for item_data in items_data:
            # Remove user from item_data to avoid constraint issues
            item_data.pop('user', None)
            
            item_id = item_data.get('id')
            if item_id:
                if item_id in current_item_ids:
                    item = current_items.get(id=item_id)
                    for attr, value in item_data.items():
                        setattr(item, attr, value)
                    item.save()
                    updated_item_ids.add(item_id)
                else:
                    # If ID is provided but doesn't exist, create new item
                    ChecklistItem.objects.create(
                        checklist=instance, 
                        user=instance.user,
                        **item_data
                    )
            else:
                # If no ID is provided, create new item
                ChecklistItem.objects.create(
                    checklist=instance, 
                    user=instance.user,
                    **item_data
                )
        
        # Delete items that are not in the updated data
        items_to_delete = current_item_ids - updated_item_ids
        instance.checklistitem_set.filter(id__in=items_to_delete).delete()
        
        return instance
