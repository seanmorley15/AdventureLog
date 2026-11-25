"""Removing everything a user has in the adventures app."""

from adventures.models import (
    Activity, Category, Checklist, ChecklistItem, Collection, CollectionItineraryItem,
    ContentAttachment, ContentImage, Location, Lodging, Note, Trail, Transportation,
)
from adventures.services import travelers
from worldtravel.models import VisitedCity, VisitedRegion


def clear_user_adventure_data(user) -> None:
    """Remove all adventure and world-travel data owned by the user."""
    # Places other people own, in collections that go away with this user, stay with their
    # travelers as copies. Done first: their own places are deleted below.
    travelers.release_collections_travelers(Collection.objects.filter(user=user), exclude=user)
    CollectionItineraryItem.objects.filter(collection__user=user).delete()

    for activity in Activity.objects.filter(user=user):
        if activity.gpx_file:
            activity.gpx_file.delete(save=False)

    for image in ContentImage.objects.filter(user=user):
        image.delete()

    for attachment in ContentAttachment.objects.filter(user=user):
        attachment.delete()

    Activity.objects.filter(user=user).delete()
    Trail.objects.filter(user=user).delete()
    ChecklistItem.objects.filter(user=user).delete()
    Checklist.objects.filter(user=user).delete()
    Note.objects.filter(user=user).delete()
    Transportation.objects.filter(user=user).delete()
    Lodging.objects.filter(user=user).delete()
    Location.objects.filter(user=user).delete()
    Collection.objects.filter(user=user).delete()
    Category.objects.filter(user=user).delete()
    VisitedCity.objects.filter(user=user).delete()
    VisitedRegion.objects.filter(user=user).delete()
