from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import AdventureViewSet

router = DefaultRouter()
router.register(r'adventures', AdventureViewSet, basename='adventures')

urlpatterns = [
    # Include the router under the 'api/' prefix
    path('', include(router.urls)),
]
