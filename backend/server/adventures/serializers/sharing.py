"""Who a collection is shared with: invites, members and their roles, guest links."""

from rest_framework import serializers

from adventures.models import Collection, CollectionMember

ROLES = CollectionMember.Role.choices


class InviteCreateSerializer(serializers.Serializer):
    user = serializers.UUIDField(help_text='The `uuid` of a user with a public profile.')
    role = serializers.ChoiceField(choices=ROLES, default='editor')


class MemberRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=ROLES)


class GuestLinkCreateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=ROLES, default='viewer')
    label = serializers.CharField(required=False, allow_blank=True, default='', max_length=100)
    expires_at = serializers.DateTimeField(
        required=False, allow_null=True, help_text='When the link stops working. Must be in the future.'
    )


class _PersonSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    username = serializers.CharField()
    first_name = serializers.CharField(allow_blank=True)
    last_name = serializers.CharField(allow_blank=True)


class SharingMemberSerializer(_PersonSerializer):
    profile_pic = serializers.CharField(allow_null=True)
    role = serializers.ChoiceField(choices=ROLES)


class SharingInviteSerializer(_PersonSerializer):
    role = serializers.ChoiceField(choices=ROLES)


class GuestLinkSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    token = serializers.CharField(help_text='Add `?guest=<token>` to the collection page address to use the link.')
    role = serializers.ChoiceField(choices=ROLES)
    label = serializers.CharField(allow_blank=True)
    expires_at = serializers.DateTimeField(allow_null=True)
    revoked_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
    is_active = serializers.BooleanField()


class SharingStateSerializer(serializers.Serializer):
    owner = _PersonSerializer()
    members = SharingMemberSerializer(many=True)
    invites = SharingInviteSerializer(many=True, help_text='Invites waiting for an answer.')
    guest_links = GuestLinkSerializer(many=True)
    visibility = serializers.ChoiceField(choices=Collection.Visibility.choices)
    story_groups = serializers.DictField(
        child=serializers.BooleanField(), help_text='Which parts of the plan the public story shows.'
    )
    comment_access = serializers.CharField(help_text='Who can comment on the story.')
    share_secret = serializers.CharField(allow_null=True, help_text='The `?s=` secret of the unlisted link.')
    allow_public_links = serializers.BooleanField(help_text='Whether this server allows public and unlisted collections.')
    is_admin = serializers.BooleanField(help_text='Whether you can change that server setting.')


class ShareableUsersQuerySerializer(serializers.Serializer):
    q = serializers.CharField(
        required=False, allow_blank=True, default='', help_text='Search by name or username (2+ characters).'
    )
    limit = serializers.IntegerField(default=20, min_value=1, max_value=50)


class ShareableUserSerializer(_PersonSerializer):
    profile_pic = serializers.CharField(allow_null=True)
    status = serializers.CharField(help_text='Always `available`.')
