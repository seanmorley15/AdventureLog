"""Comments on a collection, the comment inbox, and the activity feed."""

from rest_framework import serializers

THREADS = ['plan', 'story']


class ThreadQuerySerializer(serializers.Serializer):
    thread = serializers.ChoiceField(
        choices=THREADS, default='plan',
        help_text="`plan`: members' discussion of the plan. `story`: comments on the public story.",
    )
    s = serializers.CharField(required=False, help_text='The share secret, to read an unlisted story.')


class CommentCreateSerializer(serializers.Serializer):
    thread = serializers.ChoiceField(choices=THREADS, default='plan')
    body = serializers.CharField(max_length=4000, help_text='Plain text. `@username` mentions a member (plan only).')
    parent = serializers.UUIDField(required=False, allow_null=True, help_text='Reply to this comment.')
    day = serializers.UUIDField(required=False, allow_null=True, help_text='Plan only: the trip day it is about.')
    placement = serializers.UUIDField(required=False, allow_null=True, help_text='Plan only: the itinerary item it is about.')


class CommentUpdateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=4000)


class CommentAuthorSerializer(serializers.Serializer):
    name = serializers.CharField()
    username = serializers.CharField(allow_null=True)
    uuid = serializers.UUIDField(allow_null=True)
    profile_pic = serializers.CharField(allow_null=True)
    can_view_profile = serializers.BooleanField()
    is_guest = serializers.BooleanField(help_text='Written through a guest link, without an account.')


class CommentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    is_story = serializers.BooleanField()
    parent = serializers.UUIDField(allow_null=True)
    day_index = serializers.IntegerField(allow_null=True)
    body = serializers.CharField()
    created_at = serializers.DateTimeField()
    edited_at = serializers.DateTimeField(allow_null=True)
    author = CommentAuthorSerializer()
    can_edit = serializers.BooleanField()
    can_delete = serializers.BooleanField()
    day = serializers.UUIDField(required=False, allow_null=True, help_text='Plan comments only.')
    placement = serializers.UUIDField(required=False, allow_null=True, help_text='Plan comments only.')
    mentions = serializers.ListField(child=serializers.CharField(), required=False, help_text='Plan comments only.')


class CommentWithRepliesSerializer(CommentSerializer):
    replies = CommentSerializer(many=True)


class CommentThreadSerializer(serializers.Serializer):
    thread = serializers.ChoiceField(choices=THREADS)
    comment_access = serializers.CharField(help_text='Who may comment on the story.')
    can_post = serializers.BooleanField(help_text='Whether you can post in this thread.')
    comments = CommentWithRepliesSerializer(many=True, help_text='Top-level comments, oldest first.')


class InboxQuerySerializer(serializers.Serializer):
    limit = serializers.IntegerField(default=30, min_value=1, max_value=100)


class InboxCommentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    collection = serializers.DictField(help_text='`{id, name}`')
    thread = serializers.ChoiceField(choices=THREADS)
    day_index = serializers.IntegerField(allow_null=True)
    author_name = serializers.CharField()
    author = serializers.DictField()
    excerpt = serializers.CharField()
    created_at = serializers.DateTimeField()
    mentions_me = serializers.BooleanField()
    unread = serializers.BooleanField()


class InboxSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()
    comments = InboxCommentSerializer(many=True, help_text='Newest first.')


class UnreadCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()


class ActivityFeedQuerySerializer(serializers.Serializer):
    limit = serializers.IntegerField(default=50, min_value=1, max_value=200)


class ActivityEventSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    verb = serializers.CharField(help_text='What happened, e.g. `item_moved`, `member_added`, `comment_added`.')
    actor_name = serializers.CharField()
    actor = serializers.DictField()
    data = serializers.DictField(help_text='Details that depend on `verb`.')
    created_at = serializers.DateTimeField()
