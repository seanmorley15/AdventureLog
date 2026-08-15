from rest_framework import serializers

from .models import Subscription


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = [
            "stripe_subscription_id",
            "status",
            "trial_ends_at",
            "current_period_ends_at",
            "cancel_at_period_end",
        ]
        read_only_fields = fields
