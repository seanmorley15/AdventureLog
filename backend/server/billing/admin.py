from django.conf import settings
from django.contrib import admin

from .models import Subscription


if settings.CLOUD_MODE:
    @admin.register(Subscription)
    class SubscriptionAdmin(admin.ModelAdmin):
        list_display = (
            "user",
            "status",
            "trial_ends_at",
            "current_period_ends_at",
            "cancel_at_period_end",
        )
        search_fields = ("user__username", "stripe_customer_id", "stripe_subscription_id")
        list_filter = ("status", "cancel_at_period_end")
