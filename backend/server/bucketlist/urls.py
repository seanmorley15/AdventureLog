from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BucketItemViewSet

router = DefaultRouter()
router.register(r'items', BucketItemViewSet, basename='bucketitem')

urlpatterns = [
    path('bucketlist/', include(router.urls)),
]
