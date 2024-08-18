from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import AdventureViewSet, ChecklistViewSet, CollectionViewSet, NoteViewSet, StatsViewSet, GenerateDescription, ActivityTypesView, TransportationViewSet, AdventureImageViewSet

router = DefaultRouter()
router.register(r'adventures', AdventureViewSet, basename='adventures')
router.register(r'collections', CollectionViewSet, basename='collections')
router.register(r'stats', StatsViewSet, basename='stats')
router.register(r'generate', GenerateDescription, basename='generate')
router.register(r'activity-types', ActivityTypesView, basename='activity-types')
router.register(r'transportations', TransportationViewSet, basename='transportations')
router.register(r'notes', NoteViewSet, basename='notes')
router.register(r'checklists', ChecklistViewSet, basename='checklists')
router.register(r'images', AdventureImageViewSet, basename='images')


urlpatterns = [
    # Include the router under the 'api/' prefix
    path('', include(router.urls)),
]
