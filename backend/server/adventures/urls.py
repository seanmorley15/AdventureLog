from django.urls import include, path
from rest_framework.routers import DefaultRouter
from adventures.views import *

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
router.register(r'reverse-geocode', ReverseGeocodeViewSet, basename='reverse-geocode')
router.register(r'categories', CategoryViewSet, basename='categories')
router.register(r'ics-calendar', IcsCalendarGeneratorViewSet, basename='ics-calendar')
router.register(r'search', GlobalSearchView, basename='search')
router.register(r'attachments', AttachmentViewSet, basename='attachments')
router.register(r'lodging', LodgingViewSet, basename='lodging')
router.register(r'recommendations', RecommendationsViewSet, basename='recommendations')

urlpatterns = [
    # Include the router under the 'api/' prefix
    path('', include(router.urls)),
]
