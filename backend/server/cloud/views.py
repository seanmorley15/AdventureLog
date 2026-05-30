from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.serializers import SubscriptionSerializer
from cloud.utils import get_or_create_subscription, has_access
from users.serializers import CustomUserDetailsSerializer as PublicUserSerializer


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = []

    def get(self, request):
        user = request.user
        subscription = get_or_create_subscription(user)
        user_serializer = PublicUserSerializer(user)
        subscription_serializer = SubscriptionSerializer(subscription)

        return Response(
            {
                "user": user_serializer.data,
                "subscription": subscription_serializer.data,
                "has_access": has_access(user, subscription),
                "cloud_mode": settings.CLOUD_MODE,
            }
        )
