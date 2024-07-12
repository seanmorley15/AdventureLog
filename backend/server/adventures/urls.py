from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import AdventureViewSet, TripViewSet, StatsViewSet, GenerateDescription

router = DefaultRouter()
router.register(r'adventures', AdventureViewSet, basename='adventures')
router.register(r'trips', TripViewSet, basename='trips')
router.register(r'stats', StatsViewSet, basename='stats')
router.register(r'generate', GenerateDescription, basename='generate')


urlpatterns = [
    # Include the router under the 'api/' prefix
    path('', include(router.urls)),
]
