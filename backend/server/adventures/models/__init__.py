"""The adventures app's models, grouped by what they describe.

Every model and the helpers that migrations refer to are importable from here, so
``from adventures.models import Location`` keeps working.
"""

from .base import User, default_user
from .choices import ADVENTURE_TYPES, LODGING_TYPES, TRANSPORTATION_TYPES
from .media import ContentAttachment, ContentImage, PathAndRename, validate_file_extension
from .location import Category, Location, Visit
from .collection import (
    Collection,
    CollectionGuestLink,
    CollectionInvite,
    CollectionMember,
    default_story_groups,
    generate_guest_token,
    generate_share_secret,
)
from .discussion import CollectionActivity, CollectionComment, CommentInboxState
from .logistics import Checklist, ChecklistItem, Lodging, Note, Transportation
from .activity import Activity, Trail
from .itinerary import CollectionItineraryDay, CollectionItineraryItem

__all__ = [
    'ADVENTURE_TYPES', 'Activity', 'Category', 'Checklist', 'ChecklistItem', 'Collection',
    'CollectionActivity', 'CollectionComment', 'CollectionGuestLink', 'CollectionInvite',
    'CollectionItineraryDay', 'CollectionItineraryItem', 'CollectionMember', 'CommentInboxState',
    'ContentAttachment', 'ContentImage', 'LODGING_TYPES', 'Location', 'Lodging', 'Note',
    'PathAndRename', 'TRANSPORTATION_TYPES', 'Trail', 'Transportation', 'User', 'Visit',
    'default_story_groups', 'default_user', 'generate_guest_token', 'generate_share_secret',
    'validate_file_extension',
]
