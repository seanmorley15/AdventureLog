from rest_framework import viewsets, permissions
from .models import BucketItem
from .serializers import BucketItemSerializer
from django.db.models import Q


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            # Allow read for public items
            return obj.is_public or (request.user and request.user.is_authenticated and obj.user == request.user)
        # Write permissions only for owner
        return request.user and request.user.is_authenticated and obj.user == request.user


class BucketItemViewSet(viewsets.ModelViewSet):
    serializer_class = BucketItemSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        qs = BucketItem.objects.select_related('location')
        if user and user.is_authenticated:
            # return user's items and public items
            return qs.filter(Q(user=user) | Q(is_public=True))
        return qs.filter(is_public=True)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
