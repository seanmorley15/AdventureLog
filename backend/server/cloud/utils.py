from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from billing.models import Subscription


def get_or_create_subscription(user) -> Subscription:
    if settings.CLOUD_MODE:
        trial_ends_at = timezone.now() + timedelta(days=settings.CLOUD_TRIAL_DAYS)
        defaults = {
            "status": Subscription.STATUS_TRIAL,
            "trial_ends_at": trial_ends_at,
        }
    else:
        defaults = {"status": Subscription.STATUS_ACTIVE, "trial_ends_at": None}

    subscription, _ = Subscription.objects.get_or_create(user=user, defaults=defaults)
    return subscription


def has_access(user, subscription: Subscription | None = None) -> bool:
    if not settings.CLOUD_MODE:
        return True

    if subscription is None:
        subscription = get_or_create_subscription(user)

    if subscription.status == Subscription.STATUS_ACTIVE:
        return True

    if subscription.status == Subscription.STATUS_TRIAL:
        if subscription.trial_ends_at is None:
            return True
        return subscription.trial_ends_at >= timezone.now()

    return False
