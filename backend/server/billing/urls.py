from django.urls import path

from .views import CreateCheckoutSessionView, CreatePortalSessionView, StripeWebhookView, SubscriptionStatusView


urlpatterns = [
    path("create-checkout-session/", CreateCheckoutSessionView.as_view(), name="billing-checkout"),
    path("create-portal-session/", CreatePortalSessionView.as_view(), name="billing-portal"),
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
    path("subscription/", SubscriptionStatusView.as_view(), name="billing-subscription"),
]
