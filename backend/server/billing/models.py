from django.conf import settings
from django.db import models


class Subscription(models.Model):
    STATUS_TRIAL = "trial"
    STATUS_ACTIVE = "active"
    STATUS_CANCELED = "canceled"
    STATUS_PAST_DUE = "past_due"

    STATUS_CHOICES = (
        (STATUS_TRIAL, "Trial"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_CANCELED, "Canceled"),
        (STATUS_PAST_DUE, "Past Due"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default=STATUS_TRIAL)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_ends_at = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} ({self.status})"


class StripeWebhookEvent(models.Model):
    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=255)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-processed_at"]

    def __str__(self):
        return f"{self.event_type} ({self.event_id})"
