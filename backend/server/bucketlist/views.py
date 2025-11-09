from rest_framework import viewsets, permissions
from .models import BucketItem
from .serializers import BucketItemSerializer
from django.db.models import Q


class BucketItemViewSet(viewsets.ModelViewSet):
    serializer_class = BucketItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user and user.is_authenticated:
            # return user's items only
            return BucketItem.objects.filter(user=user)
        return BucketItem.objects.none()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
