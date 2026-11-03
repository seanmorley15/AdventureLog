"""What ``GET /api/collections/{id}/`` returns: the collection with its day plan, or its public story."""

from rest_framework import serializers

from adventures.models import Collection

from .activity import ActivitySerializer, TrailSerializer
from .backup import RestoreSummarySerializer
from .collection import CollectionSerializer
from .itinerary import CollectionItineraryDaySerializer, CollectionItineraryItemSerializer

COLLECTION_ORDERING = ['name', '-name', 'updated_at', '-updated_at', 'start_date', '-start_date']


class CollectionListQuerySerializer(serializers.Serializer):
    membership = serializers.ChoiceField(
        choices=['owned', 'shared'], default='owned',
        help_text='`owned`: collections you own. `shared`: collections others shared with you.',
    )
    archived = serializers.BooleanField(
        required=False, allow_null=True, default=None,
        help_text='Only archived (`true`) or only active (`false`) collections. Your own collections default to '
        'active only; shared ones to both.',
    )
    type = serializers.ChoiceField(choices=Collection.Type.choices, required=False)
    status = serializers.ChoiceField(
        choices=['upcoming', 'in_progress', 'completed'], required=False, help_text='By the trip dates.'
    )
    ordering = serializers.ChoiceField(
        choices=COLLECTION_ORDERING, default='name',
        help_text='Collections without a start date come last when sorting by it.',
    )


class _AudienceSerializer(serializers.Serializer):
    role = serializers.CharField(allow_null=True)
    is_owner = serializers.BooleanField()
    can_edit = serializers.BooleanField()
    is_member = serializers.BooleanField()
    is_guest = serializers.BooleanField()


class CollectionDetailSerializer(CollectionSerializer):
    """A collection with its day plan, for members."""

    itinerary = CollectionItineraryItemSerializer(many=True, read_only=True, help_text='Every placement in the plan.')
    itinerary_days = CollectionItineraryDaySerializer(many=True, read_only=True)
    day_activities = ActivitySerializer(many=True, read_only=True, help_text='Activities on trip days and in Ideas.')
    day_trails = TrailSerializer(many=True, read_only=True, help_text='Trails on trip days and in Ideas.')
    day_images = serializers.ListField(child=serializers.DictField(), read_only=True, help_text='Photos of trip days.')

    class Meta(CollectionSerializer.Meta):
        fields = [*CollectionSerializer.Meta.fields, 'itinerary', 'itinerary_days', 'day_activities', 'day_trails',
                  'day_images']


class CollectionStorySerializer(serializers.Serializer):
    """
    What a public reader sees: the collection's public fields and the parts of the plan its
    `story_groups` allow, without private notes or members' account details.
    """

    id = serializers.UUIDField()
    name = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    start_date = serializers.DateField(allow_null=True)
    end_date = serializers.DateField(allow_null=True)
    story_groups = serializers.DictField(child=serializers.BooleanField())
    primary_image = serializers.DictField(allow_null=True)
    collaborators = serializers.ListField(child=serializers.DictField())
    locations = serializers.ListField(child=serializers.DictField())
    lodging = serializers.ListField(child=serializers.DictField())
    transportations = serializers.ListField(child=serializers.DictField())
    notes = serializers.ListField(child=serializers.DictField())
    checklists = serializers.ListField(child=serializers.DictField())
    itinerary = serializers.ListField(child=serializers.DictField())
    itinerary_days = serializers.ListField(child=serializers.DictField())
    day_activities = serializers.ListField(child=serializers.DictField())
    day_trails = serializers.ListField(child=serializers.DictField())
    day_images = serializers.ListField(child=serializers.DictField())
    audience = _AudienceSerializer()
    story_preview = serializers.BooleanField(help_text='True when a member asked for the story with `as=story`.')


class CollectionImportResultSerializer(CollectionSerializer):
    import_summary = RestoreSummarySerializer(read_only=True, help_text='What the archive added.')

    class Meta(CollectionSerializer.Meta):
        fields = [*CollectionSerializer.Meta.fields, 'import_summary']
