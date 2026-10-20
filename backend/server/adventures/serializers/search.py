"""Global search results."""

from rest_framework import serializers

class SearchHitSerializer(serializers.Serializer):
    type = serializers.CharField()
    id = serializers.CharField()
    title = serializers.CharField()
    subtitle = serializers.CharField(allow_blank=True)
    url = serializers.CharField()
    score = serializers.FloatField()
    meta = serializers.DictField(required=False, default=dict)
