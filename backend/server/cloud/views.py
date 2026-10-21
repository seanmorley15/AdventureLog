"""The account as hosted (cloud) servers show it: with the subscription that gates access."""

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import serializers

from billing.serializers import SubscriptionSerializer
from cloud.utils import get_or_create_subscription, has_access
from users.serializers import AccountSerializer
from users.views import AccountViewSet as BaseAccountViewSet


class HostedAccountSerializer(AccountSerializer):
    subscription = SubscriptionSerializer(
        help_text='The billing state. Self-hosted servers always grant access, whatever it says.'
    )
    has_access = serializers.BooleanField(
        help_text='False when a hosted server requires a subscription this account does not have. '
        'Most endpoints then answer 402.'
    )
    cloud_mode = serializers.BooleanField(help_text='True on hosted servers with billing.')


class AccountViewSet(BaseAccountViewSet):
    def account_extras(self, user):
        subscription = get_or_create_subscription(user)
        return {
            'subscription': SubscriptionSerializer(subscription).data,
            'has_access': has_access(user, subscription),
            'cloud_mode': settings.CLOUD_MODE,
        }

    @extend_schema(responses=HostedAccountSerializer)
    def retrieve(self, request):
        return super().retrieve(request)

    retrieve.__doc__ = BaseAccountViewSet.retrieve.__doc__
