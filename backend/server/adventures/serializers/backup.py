"""Uploading and restoring backups and collection archives."""

from rest_framework import serializers


class RestoreSummarySerializer(serializers.Serializer):
    categories = serializers.IntegerField()
    collections = serializers.IntegerField()
    locations = serializers.IntegerField()
    locations_linked = serializers.IntegerField(
        required=False, help_text='Places in the file you already had, linked instead of copied.'
    )
    transportation = serializers.IntegerField()
    notes = serializers.IntegerField()
    checklists = serializers.IntegerField()
    checklist_items = serializers.IntegerField()
    lodging = serializers.IntegerField()
    images = serializers.IntegerField()
    attachments = serializers.IntegerField()
    visited_cities = serializers.IntegerField()
    visited_regions = serializers.IntegerField()
    trails = serializers.IntegerField()
    trails_skipped = serializers.IntegerField()
    activities = serializers.IntegerField()
    gpx_files = serializers.IntegerField()
    itinerary_items = serializers.IntegerField()


class BackupImportSerializer(serializers.Serializer):
    file = serializers.FileField(help_text='A zip file from `GET /api/backup/export/`.')
    confirm = serializers.ChoiceField(
        choices=['yes'], help_text='Must be `yes`: restoring deletes everything in the account first.'
    )


class BackupImportResultSerializer(serializers.Serializer):
    summary = RestoreSummarySerializer()


class CollectionImportSerializer(serializers.Serializer):
    file = serializers.FileField(help_text='A zip file from `GET /api/collections/{id}/archive/`.')
    existing_locations = serializers.ChoiceField(
        choices=['link', 'create'],
        default='link',
        help_text='For places in the file you already have: `link` uses yours, `create` makes copies.',
    )
