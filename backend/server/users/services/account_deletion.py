import logging

from django.conf import settings
from django.db import transaction

from adventures.models import Collection, CollectionInvite
from adventures.services.account_data import clear_user_adventure_data
from core.errors import ServiceError
from core.lazy import lazy_module

# stripe costs ~40 MB and ~3 s to import; load it only when billing code actually runs.
stripe = lazy_module('stripe')

logger = logging.getLogger(__name__)


class AccountDeletionError(ServiceError):
    """Raised when account deletion cannot be completed."""

    status = 502
    code = 'billing_cleanup_failed'


def cancel_stripe_billing(user) -> None:
    """Cancel any active Stripe subscription and delete the Stripe customer."""
    if not settings.CLOUD_MODE or not settings.STRIPE_SECRET_KEY:
        return

    try:
        subscription = user.subscription
    except Exception:
        return

    from stripe.error import InvalidRequestError

    stripe.api_key = settings.STRIPE_SECRET_KEY

    if subscription.stripe_subscription_id:
        try:
            stripe.Subscription.cancel(subscription.stripe_subscription_id)
        except InvalidRequestError as exc:
            if "No such subscription" not in str(exc):
                logger.exception("Failed to cancel Stripe subscription for user %s", user.pk)
                raise AccountDeletionError(
                    "Unable to cancel your subscription. Please try again or contact support."
                ) from exc

    if subscription.stripe_customer_id:
        try:
            stripe.Customer.delete(subscription.stripe_customer_id)
        except InvalidRequestError as exc:
            if "No such customer" not in str(exc):
                logger.exception("Failed to delete Stripe customer for user %s", user.pk)
                raise AccountDeletionError(
                    "Unable to remove your billing profile. Please try again or contact support."
                ) from exc


def _detach_sharing(user) -> None:
    """Take the user off other people's visits and remove them from shared collections and pending invites."""
    from adventures.models import Visit
    from adventures.services import travelers

    # A visit they were the last traveler on goes with them; their own locations are cleared separately.
    for visit in Visit.objects.filter(travelers=user).exclude(location__user=user).select_related('location'):
        travelers.remove_or_delete(visit, user)
    for collection in Collection.objects.filter(shared_with=user):
        collection.shared_with.remove(user)
    CollectionInvite.objects.filter(invited_user=user).delete()


def _delete_profile_pic(user) -> None:
    if user.profile_pic:
        user.profile_pic.delete(save=False)


@transaction.atomic
def _delete_user_data(user) -> None:
    _detach_sharing(user)
    clear_user_adventure_data(user)
    _delete_profile_pic(user)
    user.delete()


def delete_user_account(user) -> None:
    """
    Permanently delete a user account and all associated data.

    Stripe billing is cancelled before the database transaction so a billing
    failure does not leave a paid subscription attached to a deleted account.
    """
    cancel_stripe_billing(user)
    _delete_user_data(user)
