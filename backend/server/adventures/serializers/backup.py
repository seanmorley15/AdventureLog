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


class CollectionPdfOptionsSerializer(serializers.Serializer):
    """What to put in the PDF. Anything left out takes a default that suits the collection and the person."""

    paper = serializers.ChoiceField(
        choices=['a4', 'letter'], required=False,
        help_text='Page size. Defaults to Letter for people who use imperial units, otherwise A4.',
    )
    photos = serializers.BooleanField(
        required=False, default=True,
        help_text='Include photos. Turn off for a smaller file that uses less ink.',
    )
    # allow_null: DRF reads a boolean missing from query parameters as False, and "not chosen"
    # must stay different from "off".
    journal = serializers.BooleanField(
        required=False, allow_null=True, default=None,
        help_text='Add space to write: notes lines on each day of a trip, and boxes, lines and ratings to fill in for a folder. '
                  'Defaults to on for a folder and off for a trip.',
    )
