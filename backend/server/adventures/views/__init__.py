"""The adventures API views, one module per resource. Routes are registered in ``adventures.urls``."""

from .activities import ActivityViewSet
from .attachments import AttachmentViewSet
from .backup import BackupViewSet
from .calendar import CalendarViewSet
from .categories import CategoryViewSet
from .checklists import ChecklistViewSet
from .collections import CollectionViewSet
from .dashboard import DashboardView
from .discussion import CollectionActivityViewSet, CollectionCommentViewSet, CommentViewSet
from .images import ContentImageViewSet
from .itineraries import CollectionDayViewSet, ItineraryItemViewSet, ItineraryViewSet
from .locations import LocationViewSet
from .lodging import LodgingViewSet
from .notes import NoteViewSet
from .places import PlacesViewSet
from .recommendations import RecommendationsViewSet
from .search import SearchViewSet
from .tags import TagViewSet
from .trails import TrailViewSet
from .transportation import TransportationViewSet
from .visited_regions import VisitedRegionSyncView
from .visits import VisitViewSet

__all__ = [
    'ActivityViewSet',
    'AttachmentViewSet',
    'BackupViewSet',
    'CalendarViewSet',
    'CategoryViewSet',
    'ChecklistViewSet',
    'CollectionActivityViewSet',
    'CollectionCommentViewSet',
    'CollectionDayViewSet',
    'CollectionViewSet',
    'CommentViewSet',
    'ContentImageViewSet',
    'DashboardView',
    'ItineraryItemViewSet',
    'ItineraryViewSet',
    'LocationViewSet',
    'LodgingViewSet',
    'NoteViewSet',
    'PlacesViewSet',
    'RecommendationsViewSet',
    'SearchViewSet',
    'TagViewSet',
    'TrailViewSet',
    'TransportationViewSet',
    'VisitViewSet',
    'VisitedRegionSyncView',
]
