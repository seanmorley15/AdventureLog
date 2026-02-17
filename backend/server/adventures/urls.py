from django.urls import include, path
from rest_framework.routers import DefaultRouter
from adventures.views import *

router = DefaultRouter()
router.register(r'locations', LocationViewSet, basename='locations')
router.register(r'collections', CollectionViewSet, basename='collections')
router.register(r'stats', StatsViewSet, basename='stats')
router.register(r'generate', GenerateDescription, basename='generate')
router.register(r'tags', ActivityTypesView, basename='tags')
router.register(r'transportations', TransportationViewSet, basename='transportations')
router.register(r'notes', NoteViewSet, basename='notes')
router.register(r'checklists', ChecklistViewSet, basename='checklists')
router.register(r'images', ContentImageViewSet, basename='images')
router.register(r'reverse-geocode', ReverseGeocodeViewSet, basename='reverse-geocode')
router.register(r'categories', CategoryViewSet, basename='categories')
router.register(r'ics-calendar', IcsCalendarGeneratorViewSet, basename='ics-calendar')
router.register(r'search', GlobalSearchView, basename='search')
router.register(r'attachments', AttachmentViewSet, basename='attachments')
router.register(r'lodging', LodgingViewSet, basename='lodging')
router.register(r'recommendations', RecommendationsViewSet, basename='recommendations'),
router.register(r'backup', BackupViewSet, basename='backup')
router.register(r'trails', TrailViewSet, basename='trails')
router.register(r'activities', ActivityViewSet, basename='activities')
router.register(r'visits', VisitViewSet, basename='visits')
router.register(r'itineraries', ItineraryViewSet, basename='itineraries')
router.register(r'itinerary-days', ItineraryDayViewSet, basename='itinerary-days')
router.register(r'collection-templates', CollectionTemplateViewSet, basename='collection-templates')
router.register(r'transportation-types', TransportationTypeViewSet, basename='transportation-types')
router.register(r'lodging-types', LodgingTypeViewSet, basename='lodging-types')
router.register(r'adventure-types', AdventureTypeViewSet, basename='adventure-types')
router.register(r'activity-types', ActivityTypeViewSet, basename='activity-types')

urlpatterns = [
    # Include the router under the 'api/' prefix
    path('', include(router.urls)),
]
