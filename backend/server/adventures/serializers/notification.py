"""The notification inbox."""

from rest_framework import serializers


class NotificationQuerySerializer(serializers.Serializer):
    unread = serializers.BooleanField(default=False, help_text='Only notifications you have not read.')


class NotificationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.CharField(help_text='What happened. Today only `visit_traveler_added`.')
    actor = serializers.DictField(help_text='Who did it: `{name, username, uuid, profile_pic, can_view_profile}`.')
    visit_id = serializers.UUIDField(
        allow_null=True, help_text='The visit, when it was one visit. `POST /api/visits/{id}/leave/` removes you.'
    )
    location_id = serializers.UUIDField(
        allow_null=True, help_text='The place, when it was one place and you can still read it.'
    )
    location_name = serializers.CharField(help_text='Empty when you can no longer read the place.')
    collection_id = serializers.UUIDField(allow_null=True, help_text='The trip, while you are still a member.')
    collection_name = serializers.CharField(help_text='Empty when you are no longer a member of the trip.')
    count = serializers.IntegerField(help_text='How many visits. More than 1 is the summary form.')
    locations = serializers.IntegerField(help_text='How many places those visits were at.')
    start_date = serializers.DateField(allow_null=True)
    end_date = serializers.DateField(allow_null=True)
    created_at = serializers.DateTimeField()
    read = serializers.BooleanField()


class MarkNotificationsReadSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=True, max_length=1000,
        help_text='Only these. Leave it out to mark every notification read.',
    )
