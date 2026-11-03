"""Serializers for the adventures app, split by what they describe.

Every name is re-exported here, so ``from adventures.serializers import X`` keeps working."""

from .common import (
    _build_profile_pic_url,
    _member_roles,
    _serialize_collaborator,
)
from .media import (
    _immich_integration_for,
    ContentImageSerializer,
    ImageMapPinSerializer,
    AttachmentSerializer,
    MediaFieldsMixin,
)
from .activity import (
    TrailSerializer,
    ActivitySerializer,
    VisitSerializer,
    LocationVisitSerializer,
)
from .location import (
    CategorySerializer,
    LocationListSerializer,
    LocationSerializer,
    MapPinSerializer,
)
from .logistics import (
    TransportationSerializer,
    LodgingSerializer,
    NoteSerializer,
    ChecklistItemSerializer,
    ChecklistSerializer,
)
from .collection import (
    CollectionSummaryMixin,
    CollectionSerializer,
    _load_collection_images,
    CollectionInviteSerializer,
    UltraSlimCollectionSerializer,
)
from .itinerary import (
    CollectionItineraryDaySerializer,
    CollectionItineraryItemSerializer,
    add_quick_add_extras,
    plan_state,
    serialize_updated_object,
)
from .search import (
    SearchHitSerializer,
)
