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
            "created_at",
        )
        search_fields = ("user__username", "stripe_customer_id", "stripe_subscription_id")
        list_filter = ("status", "cancel_at_period_end")
        autocomplete_fields = ("user",)
        readonly_fields = ("created_at", "updated_at")
        date_hierarchy = "trial_ends_at"

        fieldsets = (
            (None, {"fields": ("user", "status", "cancel_at_period_end")}),
            (
                "Stripe",
                {
                    "fields": ("stripe_customer_id", "stripe_subscription_id"),
                },
            ),
            (
                "Billing periods",
                {
                    "fields": ("trial_ends_at", "current_period_ends_at"),
                },
            ),
            (
                "Metadata",
                {"classes": ("collapse",), "fields": ("created_at", "updated_at")},
            ),
        )
