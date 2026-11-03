from django.urls import path

from .views import CreateCheckoutSessionView, CreatePortalSessionView, StripeWebhookView


urlpatterns = [
    path("checkout-session/", CreateCheckoutSessionView.as_view(), name="billing-checkout"),
    path("portal-session/", CreatePortalSessionView.as_view(), name="billing-portal"),
    # Configured in the Stripe dashboard; keep this path stable.
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
]
