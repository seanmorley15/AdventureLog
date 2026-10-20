from rest_framework import serializers

def get_user_uuid(user):
    return str(user.uuid)

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
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if hasattr(instance, 'user') and instance.user:
            representation['user'] = get_user_uuid(instance.user)
        return representation