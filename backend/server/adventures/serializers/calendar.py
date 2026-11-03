"""Calendar events and the dashboard that shows the upcoming ones."""

from rest_framework import serializers

from .collection import UltraSlimCollectionSerializer
from .location import LocationSerializer

EVENT_TYPES = ['visit', 'transportation', 'lodging', 'collection', 'note', 'checklist', 'stop', 'activity']


class CalendarQuerySerializer(serializers.Serializer):
    start = serializers.DateField(required=False, help_text='First day to include (YYYY-MM-DD).')
    end = serializers.DateField(required=False, help_text='Last day to include (YYYY-MM-DD).')
    types = serializers.CharField(
        required=False,
        help_text='Comma-separated event types to include: ' + ', '.join(f'`{t}`' for t in EVENT_TYPES)
        + '. All by default.',
    )


class CalendarEventSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.ChoiceField(choices=EVENT_TYPES)
    title = serializers.CharField()
    start = serializers.CharField(help_text='ISO 8601 date or date-time.')
    end = serializers.CharField(help_text='ISO 8601 date or date-time.')
    all_day = serializers.BooleanField()
    timezone = serializers.CharField(allow_null=True)
    color = serializers.CharField(help_text='A hex color for the event type.')
    icon = serializers.CharField(allow_null=True)
    category = serializers.CharField(allow_null=True)
    location_label = serializers.CharField(allow_blank=True)
    description = serializers.CharField(allow_blank=True)
    url = serializers.CharField(allow_blank=True, help_text='The app page for the event, relative to the frontend.')
    resource_id = serializers.CharField(allow_blank=True)
    collection_id = serializers.CharField(allow_null=True)
    collection_name = serializers.CharField(allow_null=True)


class CalendarEventsSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    events = CalendarEventSerializer(many=True)


class DashboardSerializer(serializers.Serializer):
    stats = serializers.JSONField(help_text='The same counts as `GET /api/users/{username}/stats/`.')
    recent_locations = LocationSerializer(many=True, help_text='Recently changed places you have visited.')
    upcoming_trips = UltraSlimCollectionSerializer(many=True)
    active_trip = UltraSlimCollectionSerializer(allow_null=True, help_text='The trip happening today, if any.')
    upcoming_events = CalendarEventSerializer(many=True)
    invite_count = serializers.IntegerField(help_text='Collection invites waiting for an answer.')
