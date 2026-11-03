from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

def get_user_uuid(user):
    return str(user.uuid)


@extend_schema_field(OpenApiTypes.UUID)
class UserUUIDField(serializers.RelatedField):
    """A user, shown by their public ``uuid`` instead of the database id. Read-only."""

    def __new__(cls, *args, **kwargs):
        # Set before RelatedField.__new__ builds the wrapper for many=True.
        kwargs['read_only'] = True
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, **kwargs):
        kwargs['read_only'] = True
        super().__init__(**kwargs)

    def to_representation(self, value):
        return str(value.uuid)

def memoized_count(serializer, bucket, key, compute):
    """
    Per-request memo for a count a nested serializer needs for many rows.

    The count is computed once per key and kept in the serializer context, which is
    shared with nested serializers. Without a shared context it simply computes.
    """
    context = serializer.context
    if not isinstance(context, dict) or not hasattr(serializer.root, '_context'):
        return compute()
    memo = context.setdefault('_count_memo', {})
    full_key = (bucket, key)
    if full_key not in memo:
        memo[full_key] = compute()
    return memo[full_key]


class CustomModelSerializer(serializers.ModelSerializer):
    """A model serializer that shows the owning ``user`` by uuid."""

    def get_fields(self):
        fields = super().get_fields()
        user = fields.get('user')
        if isinstance(user, serializers.PrimaryKeyRelatedField) and user.read_only:
            fields['user'] = UserUUIDField(help_text='The owner.')
        return fields

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if hasattr(instance, 'user') and instance.user:
            representation['user'] = get_user_uuid(instance.user)
        return representation

def validated(serializer_class, data, **kwargs):
    """
    Validate ``data`` (a request's query params or body) and return the clean values.

    Invalid input raises DRF's ``ValidationError``, which the API answers with a 400 listing
    the problem for each field. The same serializer documents the input in the schema.
    """
    serializer = serializer_class(data=data, **kwargs)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data
