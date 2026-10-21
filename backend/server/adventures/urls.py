"""
Routes of the adventures app. Mounted at ``api/`` by ``main.api_urls``.

Records that can stand alone are top-level. Records that exist only inside a collection are
nested under ``collections/<collection_id>/``. See API.md for the conventions.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.routers import SingletonRouter
from adventures.views import (
    ActivityViewSet,
    AttachmentViewSet,
    BackupViewSet,
    CalendarViewSet,
    CategoryViewSet,
    ChecklistViewSet,
    CollectionActivityViewSet,
    CollectionCommentViewSet,
    CollectionDayViewSet,
    CollectionViewSet,
    CommentViewSet,
    ContentImageViewSet,
    DashboardView,
    ItineraryItemViewSet,
    ItineraryViewSet,
    LocationViewSet,
    LodgingViewSet,
    NoteViewSet,
    PlacesViewSet,
    RecommendationsViewSet,
    SearchViewSet,
    TagViewSet,
    TrailViewSet,
    TransportationViewSet,
    VisitedRegionSyncView,
    VisitViewSet,
)

IN_COLLECTION = r'collections/(?P<collection_id>[^/.]+)'

router = DefaultRouter()
# Places and what happens at them
router.register(r'locations', LocationViewSet, basename='locations')
router.register(r'visits', VisitViewSet, basename='visits')
router.register(r'activities', ActivityViewSet, basename='activities')
router.register(r'trails', TrailViewSet, basename='trails')
router.register(r'categories', CategoryViewSet, basename='categories')
router.register(r'tags', TagViewSet, basename='tags')
# Collections and what lives only inside one
router.register(r'collections', CollectionViewSet, basename='collections')
router.register(rf'{IN_COLLECTION}/itinerary-items', ItineraryItemViewSet, basename='itinerary-items')
router.register(rf'{IN_COLLECTION}/days', CollectionDayViewSet, basename='collection-days')
router.register(rf'{IN_COLLECTION}/comments', CollectionCommentViewSet, basename='collection-comments')
router.register(rf'{IN_COLLECTION}/activity', CollectionActivityViewSet, basename='collection-activity')
router.register(r'comments', CommentViewSet, basename='comments')
# Records that can be on their own or in a collection
router.register(r'lodgings', LodgingViewSet, basename='lodgings')
router.register(r'transportations', TransportationViewSet, basename='transportations')
router.register(r'notes', NoteViewSet, basename='notes')
router.register(r'checklists', ChecklistViewSet, basename='checklists')
# Files on any record
router.register(r'images', ContentImageViewSet, basename='images')
router.register(r'attachments', AttachmentViewSet, basename='attachments')
# Lookups and account-wide views
router.register(r'places', PlacesViewSet, basename='places')
router.register(r'recommendations', RecommendationsViewSet, basename='recommendations')
router.register(r'search', SearchViewSet, basename='search')
router.register(r'calendar', CalendarViewSet, basename='calendar')
router.register(r'backup', BackupViewSet, basename='backup')

plan_router = SingletonRouter()
plan_router.register(rf'{IN_COLLECTION}/itinerary', ItineraryViewSet, basename='itinerary')

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    # Before the world travel routes, whose visited-regions/<region>/ would match it.
    path('visited-regions/sync/', VisitedRegionSyncView.as_view(), name='visited-regions-sync'),
    path('', include(plan_router.urls)),
    path('', include(router.urls)),
]
