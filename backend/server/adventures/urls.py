from django.urls import include, path
from rest_framework.routers import DefaultRouter
from adventures.views import (
    ActivityViewSet,
    AttachmentViewSet,
    BackupViewSet,
    CalendarViewSet,
    CategoryViewSet,
    ChecklistViewSet,
    CollectionActivityViewSet,
    CollectionCommentViewSet,
    CollectionViewSet,
    ContentImageViewSet,
    DescriptionViewSet,
    IcsCalendarGeneratorViewSet,
    ItineraryDayViewSet,
    ItineraryViewSet,
    LocationViewSet,
    LodgingViewSet,
    NoteViewSet,
    PlacesViewSet,
    RecommendationsViewSet,
    ReverseGeocodeViewSet,
    SearchViewSet,
    StatsViewSet,
    SunriseSunsetViewSet,
    TagViewSet,
    TrailViewSet,
    TransportationViewSet,
    VisitViewSet,
)

router = DefaultRouter()
router.register(r'locations', LocationViewSet, basename='locations')
router.register(r'collections', CollectionViewSet, basename='collections')
router.register(r'stats', StatsViewSet, basename='stats')
router.register(r'generate', DescriptionViewSet, basename='generate')
router.register(r'tags', TagViewSet, basename='tags')
router.register(r'transportations', TransportationViewSet, basename='transportations')
router.register(r'notes', NoteViewSet, basename='notes')
router.register(r'checklists', ChecklistViewSet, basename='checklists')
router.register(r'images', ContentImageViewSet, basename='images')
router.register(r'reverse-geocode', ReverseGeocodeViewSet, basename='reverse-geocode')
router.register(r'places', PlacesViewSet, basename='places')
router.register(r'sunrise-sunset', SunriseSunsetViewSet, basename='sunrise-sunset')
router.register(r'categories', CategoryViewSet, basename='categories')
router.register(r'ics-calendar', IcsCalendarGeneratorViewSet, basename='ics-calendar')
router.register(r'search', SearchViewSet, basename='search')
router.register(r'attachments', AttachmentViewSet, basename='attachments')
router.register(r'lodging', LodgingViewSet, basename='lodging')
router.register(r'recommendations', RecommendationsViewSet, basename='recommendations'),
router.register(r'backup', BackupViewSet, basename='backup')
router.register(r'trails', TrailViewSet, basename='trails')
router.register(r'activities', ActivityViewSet, basename='activities')
router.register(r'visits', VisitViewSet, basename='visits')
router.register(r'calendar', CalendarViewSet, basename='calendar')
router.register(r'itineraries', ItineraryViewSet, basename='itineraries')
router.register(r'itinerary-days', ItineraryDayViewSet, basename='itinerary-days')
router.register(r'collection-comments', CollectionCommentViewSet, basename='collection-comments')
router.register(r'collection-activity', CollectionActivityViewSet, basename='collection-activity')

urlpatterns = [
    # Include the router under the 'api/' prefix
    path('', include(router.urls)),
]
