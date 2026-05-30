from datetime import datetime, timezone as dt_timezone

import stripe
from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cloud.utils import get_or_create_subscription
from .models import Subscription
from .serializers import SubscriptionSerializer


def _get_billing_email(user):
    try:
        from allauth.account.models import EmailAddress
    except Exception:
        return user.email or None

    primary = EmailAddress.objects.filter(user=user, primary=True).first()
    if primary and primary.email:
        return primary.email

    any_email = EmailAddress.objects.filter(user=user).order_by("id").first()
    if any_email and any_email.email:
        return any_email.email

    return user.email or None


def _find_existing_customer_id(billing_email, user_id):
    if billing_email:
        try:
            existing = stripe.Customer.list(email=billing_email, limit=1)
        except stripe.error.StripeError:
            existing = None

        if existing:
            existing_data = existing.get("data", [])
            if existing_data:
                return existing_data[0].get("id")

    if user_id:
        try:
            query = f"metadata['user_id']:'{user_id}'"
            results = stripe.Customer.search(query=query, limit=1)
        except stripe.error.StripeError:
            results = None

        if results:
            results_data = results.get("data", [])
            if results_data:
                return results_data[0].get("id")

    return None


def _map_stripe_status(stripe_status: str) -> str:
    mapping = {
        "trialing": Subscription.STATUS_TRIAL,
        "active": Subscription.STATUS_ACTIVE,
        "past_due": Subscription.STATUS_PAST_DUE,
        "unpaid": Subscription.STATUS_PAST_DUE,
        "canceled": Subscription.STATUS_CANCELED,
        "incomplete_expired": Subscription.STATUS_CANCELED,
    }
    return mapping.get(stripe_status, Subscription.STATUS_PAST_DUE)


def _apply_stripe_subscription(subscription: Subscription, stripe_subscription: dict) -> None:
    subscription.status = _map_stripe_status(stripe_subscription.get("status", ""))
    subscription.stripe_subscription_id = stripe_subscription.get("id", "")
    stripe_customer_id = stripe_subscription.get("customer")
    if stripe_customer_id:
        subscription.stripe_customer_id = stripe_customer_id

    subscription.cancel_at_period_end = bool(stripe_subscription.get("cancel_at_period_end", False))

    current_period_end = stripe_subscription.get("current_period_end")
    if current_period_end:
        subscription.current_period_ends_at = datetime.fromtimestamp(
            current_period_end, tz=dt_timezone.utc
        )

    trial_end = stripe_subscription.get("trial_end")
    if trial_end:
        subscription.trial_ends_at = datetime.fromtimestamp(trial_end, tz=dt_timezone.utc)

    subscription.save()


class SubscriptionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        subscription = get_or_create_subscription(request.user)
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not settings.CLOUD_MODE:
            return Response(
                {"detail": "Cloud billing is disabled for this instance."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_PRICE_ID:
            return Response(
                {"detail": "Stripe is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        subscription = get_or_create_subscription(request.user)
        if subscription.status == Subscription.STATUS_ACTIVE:
            return Response(
                {"detail": "Subscription already active."},
                status=status.HTTP_409_CONFLICT,
            )

        stripe.api_key = settings.STRIPE_SECRET_KEY

        customer_id = subscription.stripe_customer_id
        billing_email = _get_billing_email(request.user)
        if not customer_id:
            customer_id = _find_existing_customer_id(billing_email, str(request.user.id))
            if customer_id:
                subscription.stripe_customer_id = customer_id
                subscription.save()

        if not customer_id:
            customer = stripe.Customer.create(
                email=billing_email or None,
                metadata={"user_id": str(request.user.id)},
            )
            customer_id = customer.get("id")
            if customer_id:
                subscription.stripe_customer_id = customer_id
                subscription.save()

        if customer_id and billing_email:
            try:
                stripe.Customer.modify(customer_id, email=billing_email)
            except stripe.error.StripeError:
                pass

        subscription_data = {
            "metadata": {"user_id": str(request.user.id)},
        }

        if subscription.trial_ends_at and subscription.trial_ends_at > timezone.now():
            subscription_data["trial_end"] = int(subscription.trial_ends_at.timestamp())

        checkout_params = {
            "mode": "subscription",
            "line_items": [{"price": settings.STRIPE_PRICE_ID, "quantity": 1}],
            "success_url": f"{settings.FRONTEND_URL}/subscribe?success=1",
            "cancel_url": f"{settings.FRONTEND_URL}/subscribe?canceled=1",
            "client_reference_id": str(request.user.id),
            "subscription_data": subscription_data,
        }

        if customer_id:
            checkout_params["customer"] = customer_id
        elif billing_email:
            checkout_params["customer_email"] = billing_email

        try:
            session = stripe.checkout.Session.create(**checkout_params)
        except stripe.error.StripeError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({"url": session.url}, status=status.HTTP_200_OK)


class CreatePortalSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not settings.CLOUD_MODE:
            return Response(
                {"detail": "Cloud billing is disabled for this instance."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not settings.STRIPE_SECRET_KEY:
            return Response(
                {"detail": "Stripe is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        subscription = get_or_create_subscription(request.user)
        if not subscription.stripe_customer_id:
            return Response(
                {"detail": "No Stripe customer exists for this account."},
                status=status.HTTP_409_CONFLICT,
            )

        stripe.api_key = settings.STRIPE_SECRET_KEY

        try:
            session = stripe.billing_portal.Session.create(
                customer=subscription.stripe_customer_id,
                return_url=f"{settings.FRONTEND_URL}/subscribe",
            )
        except stripe.error.StripeError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({"url": session.url}, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_WEBHOOK_SECRET:
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)

        stripe.api_key = settings.STRIPE_SECRET_KEY
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        event_type = event.get("type")
        data = event.get("data", {}).get("object", {})

        if event_type == "checkout.session.completed":
            user_id = data.get("client_reference_id")
            customer_id = data.get("customer")
            subscription_id = data.get("subscription")

            subscription = None
            if user_id:
                subscription = Subscription.objects.filter(user_id=user_id).first()
            if subscription is None and customer_id:
                subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()

            if subscription:
                if customer_id:
                    subscription.stripe_customer_id = customer_id
                if subscription_id:
                    subscription.stripe_subscription_id = subscription_id

                if subscription_id:
                    try:
                        stripe_subscription = stripe.Subscription.retrieve(subscription_id)
                    except stripe.error.StripeError:
                        stripe_subscription = None

                    if stripe_subscription:
                        _apply_stripe_subscription(subscription, stripe_subscription)
                    else:
                        subscription.save()
                else:
                    subscription.save()

        if event_type in (
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ):
            stripe_subscription = data
            subscription_id = stripe_subscription.get("id")
            customer_id = stripe_subscription.get("customer")
            user_id = stripe_subscription.get("metadata", {}).get("user_id")

            subscription = None
            if subscription_id:
                subscription = Subscription.objects.filter(
                    stripe_subscription_id=subscription_id
                ).first()
            if subscription is None and customer_id:
                subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()
            if subscription is None and user_id:
                subscription = Subscription.objects.filter(user_id=user_id).first()

            if subscription:
                _apply_stripe_subscription(subscription, stripe_subscription)

        return Response(status=status.HTTP_200_OK)
