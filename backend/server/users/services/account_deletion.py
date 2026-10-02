import logging

import stripe
from stripe.error import InvalidRequestError
from django.conf import settings
from django.db import transaction

from adventures.models import (
    Activity,
    Category,
    Checklist,
    ChecklistItem,
    Collection,
    CollectionInvite,
    CollectionItineraryItem,
    ContentAttachment,
    ContentImage,
    Location,
    Lodging,
    Note,
    Trail,
    Transportation,
)
from worldtravel.models import VisitedCity, VisitedRegion

logger = logging.getLogger(__name__)


class AccountDeletionError(Exception):
    """Raised when account deletion cannot be completed."""


def clear_user_adventure_data(user) -> None:
    """Remove all adventure and world-travel data owned by the user."""
    CollectionItineraryItem.objects.filter(collection__user=user).delete()

    for activity in Activity.objects.filter(user=user):
        if activity.gpx_file:
            activity.gpx_file.delete(save=False)

    for image in ContentImage.objects.filter(user=user):
        image.delete()

    for attachment in ContentAttachment.objects.filter(user=user):
        attachment.delete()

    Activity.objects.filter(user=user).delete()
    Trail.objects.filter(user=user).delete()
    ChecklistItem.objects.filter(user=user).delete()
    Checklist.objects.filter(user=user).delete()
    Note.objects.filter(user=user).delete()
    Transportation.objects.filter(user=user).delete()
    Lodging.objects.filter(user=user).delete()
    Location.objects.filter(user=user).delete()
    Collection.objects.filter(user=user).delete()
    Category.objects.filter(user=user).delete()
    VisitedCity.objects.filter(user=user).delete()
    VisitedRegion.objects.filter(user=user).delete()


def cancel_stripe_billing(user) -> None:
    """Cancel any active Stripe subscription and delete the Stripe customer."""
    if not settings.CLOUD_MODE or not settings.STRIPE_SECRET_KEY:
        return

    try:
        subscription = user.subscription
    except Exception:
        return

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
    """Remove the user from shared collections and pending invites."""
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
