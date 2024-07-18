from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import AdventureViewSet, CollectionViewSet, StatsViewSet, GenerateDescription, ActivityTypesView

router = DefaultRouter()
router.register(r'adventures', AdventureViewSet, basename='adventures')
router.register(r'collections', CollectionViewSet, basename='collections')
router.register(r'stats', StatsViewSet, basename='stats')
router.register(r'generate', GenerateDescription, basename='generate')
router.register(r'activity-types', ActivityTypesView, basename='activity-types')


urlpatterns = [
    # Include the router under the 'api/' prefix
    path('', include(router.urls)),
]
