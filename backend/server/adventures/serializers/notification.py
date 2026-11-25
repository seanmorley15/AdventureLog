"""The notification inbox."""

from rest_framework import serializers

from adventures.models import Notification


class NotificationQuerySerializer(serializers.Serializer):
    unread = serializers.BooleanField(default=False, help_text='Only notifications you have not read.')


class NotificationActorSerializer(serializers.Serializer):
    name = serializers.CharField(help_text='How to name them: their name, a guest link label, or empty.')
    username = serializers.CharField(allow_null=True)
    uuid = serializers.UUIDField(allow_null=True)
    profile_pic = serializers.CharField(allow_null=True)
    can_view_profile = serializers.BooleanField(help_text='Whether their profile page opens for you.')


class NotificationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=Notification.Kind.choices, help_text='What happened.')
    actor = NotificationActorSerializer(help_text='Who did it.')
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
