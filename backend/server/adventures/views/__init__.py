"""The adventures API views, one module per resource. Routes are registered in ``adventures.urls``."""

from .activities import ActivityViewSet
from .attachments import AttachmentViewSet
from .backup import BackupViewSet
from .calendar import CalendarViewSet
from .categories import CategoryViewSet
from .checklists import ChecklistViewSet
from .descriptions import DescriptionViewSet
from .discussion import CollectionCommentViewSet, CollectionActivityViewSet
from .ics_calendar import IcsCalendarGeneratorViewSet
from .images import ContentImageViewSet
from .itineraries import ItineraryViewSet, ItineraryDayViewSet
from .locations import LocationViewSet
from .lodging import LodgingViewSet
from .notes import NoteViewSet
from .places import PlacesViewSet
from .recommendations import RecommendationsViewSet
from .reverse_geocode import ReverseGeocodeViewSet
from .search import SearchViewSet
from .stats import StatsViewSet
from .sunrise_sunset import SunriseSunsetViewSet
from .tags import TagViewSet
from .trails import TrailViewSet
from .transportation import TransportationViewSet
from .visits import VisitViewSet
from .collections import CollectionViewSet

__all__ = [
    'ActivityViewSet',
    'AttachmentViewSet',
    'BackupViewSet',
    'CalendarViewSet',
    'CategoryViewSet',
    'ChecklistViewSet',
    'CollectionActivityViewSet',
    'CollectionCommentViewSet',
    'CollectionViewSet',
    'ContentImageViewSet',
    'DescriptionViewSet',
    'IcsCalendarGeneratorViewSet',
    'ItineraryDayViewSet',
    'ItineraryViewSet',
    'LocationViewSet',
    'LodgingViewSet',
    'NoteViewSet',
    'PlacesViewSet',
    'RecommendationsViewSet',
    'ReverseGeocodeViewSet',
    'SearchViewSet',
    'StatsViewSet',
    'SunriseSunsetViewSet',
    'TagViewSet',
    'TrailViewSet',
    'TransportationViewSet',
    'VisitViewSet',
]
