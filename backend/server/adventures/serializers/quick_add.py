"""The quick-add request (a place picked on a map) and what it returns."""

from rest_framework import serializers

from .itinerary import CollectionItineraryItemSerializer
from .location import LocationSerializer
from .logistics import LodgingSerializer


class QuickAddSerializer(serializers.Serializer):
    """
    A place picked on the map or from search. Usually a result of `GET /api/places/search/`
    passed through. ``adventures.services.quick_add`` validates and cleans it.
    """

    name = serializers.CharField()
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    location = serializers.CharField(required=False, help_text='An address label. Reverse geocoding may replace it.')
    place_id = serializers.CharField(required=False, help_text='A Google place id; fills in missing details.')
    description = serializers.CharField(required=False)
    rating = serializers.FloatField(required=False)
    website = serializers.URLField(required=False)
    phone_number = serializers.CharField(required=False)
    google_maps_url = serializers.URLField(required=False)
    link = serializers.URLField(required=False, help_text='Defaults to the website or the Google Maps link.')
    types = serializers.ListField(
        child=serializers.CharField(), required=False, help_text='Provider place types; become tags on a location.'
    )
    photos = serializers.ListField(
        child=serializers.URLField(), required=False, help_text='Photo URLs to import (a few at most).'
    )
    category = serializers.JSONField(
        required=False,
        help_text='Locations only: a category name, or `{"name", "display_name", "icon"}` to create one.',
    )
    type = serializers.CharField(required=False, help_text='Lodging only: hotel, hostel, campground…')
    is_public = serializers.BooleanField(required=False, default=False)
    collection = serializers.UUIDField(required=False, help_text='Add it to this collection (you must be able to edit it).')
    itinerary_date = serializers.DateField(required=False, help_text='Also place it on the trip day with this date.')


class QuickAddImageImportSerializer(serializers.Serializer):
    created_count = serializers.IntegerField()
    failed_count = serializers.IntegerField()
    failed = serializers.ListField(child=serializers.DictField(), help_text='The photos that could not be imported.')


class LocationQuickAddResultSerializer(LocationSerializer):
    quick_add_itinerary_item = CollectionItineraryItemSerializer(
        required=False, help_text='Present when `itinerary_date` placed it on a day.'
    )
    quick_add_image_import = QuickAddImageImportSerializer(
        required=False, help_text='Present when some photos failed to import.'
    )

    class Meta(LocationSerializer.Meta):
        fields = [*LocationSerializer.Meta.fields, 'quick_add_itinerary_item', 'quick_add_image_import']


class LodgingQuickAddResultSerializer(LodgingSerializer):
    quick_add_itinerary_item = CollectionItineraryItemSerializer(required=False)
    quick_add_image_import = QuickAddImageImportSerializer(required=False)

    class Meta(LodgingSerializer.Meta):
        fields = [*LodgingSerializer.Meta.fields, 'quick_add_itinerary_item', 'quick_add_image_import']
