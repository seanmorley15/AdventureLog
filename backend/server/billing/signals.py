from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Subscription


User = get_user_model()


@receiver(post_save, sender=User)
def ensure_subscription(sender, instance, created, **kwargs):
    if not created:
        return

    if settings.CLOUD_MODE:
        trial_ends_at = timezone.now() + timedelta(days=settings.CLOUD_TRIAL_DAYS)
        defaults = {
            "status": Subscription.STATUS_TRIAL,
            "trial_ends_at": trial_ends_at,
        }
    else:
        defaults = {"status": Subscription.STATUS_ACTIVE, "trial_ends_at": None}

    Subscription.objects.get_or_create(user=instance, defaults=defaults)
