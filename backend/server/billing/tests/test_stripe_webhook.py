from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from billing.models import StripeWebhookEvent, Subscription

User = get_user_model()

WEBHOOK_URL = "/api/billing/webhooks/stripe/"


@override_settings(
    STRIPE_SECRET_KEY="sk_test_example",
    STRIPE_WEBHOOK_SECRET="whsec_test_example",
)
class StripeWebhookIdempotencyTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="billinguser",
            email="billinguser@example.com",
            password="testpassword",
        )
        self.subscription = Subscription.objects.get(user=self.user)

    def _subscription_updated_event(self, event_id="evt_test_123"):
        return {
            "id": event_id,
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_test_123",
                    "customer": "cus_test_123",
                    "status": "active",
                    "cancel_at_period_end": False,
                    "current_period_end": 1893456000,
                    "metadata": {"user_id": str(self.user.id)},
                }
            },
        }

    @patch("billing.views.stripe.Webhook.construct_event")
    def test_duplicate_webhook_is_ignored(self, mock_construct_event):
        mock_construct_event.return_value = self._subscription_updated_event()

        first_response = self.client.post(
            WEBHOOK_URL,
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig_test",
        )
        second_response = self.client.post(
            WEBHOOK_URL,
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig_test",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(StripeWebhookEvent.objects.count(), 1)

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, Subscription.STATUS_ACTIVE)
        self.assertEqual(self.subscription.stripe_subscription_id, "sub_test_123")
        self.assertEqual(self.subscription.stripe_customer_id, "cus_test_123")

    @patch("billing.views.stripe.Webhook.construct_event")
    def test_webhook_without_event_id_is_rejected(self, mock_construct_event):
        event = self._subscription_updated_event()
        event.pop("id")
        mock_construct_event.return_value = event

        response = self.client.post(
            WEBHOOK_URL,
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig_test",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(StripeWebhookEvent.objects.count(), 0)

    @patch("billing.views.stripe.Webhook.construct_event")
    def test_unhandled_event_type_is_recorded(self, mock_construct_event):
        mock_construct_event.return_value = {
            "id": "evt_unhandled_123",
            "type": "invoice.paid",
            "data": {"object": {}},
        }

        response = self.client.post(
            WEBHOOK_URL,
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig_test",
        )

        self.assertEqual(response.status_code, 200)
        event = StripeWebhookEvent.objects.get(event_id="evt_unhandled_123")
        self.assertEqual(event.event_type, "invoice.paid")
