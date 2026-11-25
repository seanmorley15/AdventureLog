"""What deleting an account, or making a profile private, would do to shared trips. Nothing here changes data."""

from adventures.models import Collection, CollectionInvite, Location, Visit
from adventures.services import travelers


def deletion_preview(user):
    """
    What deleting ``user``'s account would do, matching ``account_deletion._delete_user_data``.

    ``locations`` and ``collections``: what they own, all deleted. ``shared_collections_left``:
    trips they are a member of. ``people_released`` and ``places_copied``: people who travelled
    to places in their collections and would get their own copy. ``visits_detached``: visits at
    other people's places that others also travelled on, which stay without them.
    ``visits_deleted`` and ``others_uploads``: visits at other people's places they were the
    only traveler on, and what others added to them, which go.
    """
    release = travelers.release_preview(travelers.collections_release_plan(Collection.objects.filter(user=user)))
    theirs = Location.objects.filter(visits__travelers=user).exclude(user=user).distinct()
    impact = travelers.leave_preview_all_places(theirs, user)
    on_others = Visit.objects.filter(travelers=user).exclude(location__user=user).count()
    return {
        'people_released': release['people'],
        'places_copied': release['places'],
        'locations': Location.objects.filter(user=user).count(),
        'collections': Collection.objects.filter(user=user).count(),
        'shared_collections_left': Collection.objects.filter(shared_with=user).count(),
        'visits_detached': on_others - impact['visits_deleted'],
        'visits_deleted': impact['visits_deleted'],
        'others_uploads': impact['others_uploads'],
    }


def privacy_preview(user):
    """
    What making ``user``'s profile private would do: they leave every trip shared with them, keeping
    a copy of each place they travelled to there (``copies``), and their unanswered invites go.
    ``visits_deleted`` and ``others_uploads`` are the visits they were the only traveler on, and
    what others added to them.
    """
    collections = Collection.objects.filter(shared_with=user)
    impact = travelers.leave_preview_all(collections, user)
    return {
        'left_shared_collections': collections.count(),
        'revoked_collection_invites': CollectionInvite.objects.filter(invited_user=user).count(),
        'copies': impact['locations'],
        'visits_deleted': impact['visits_deleted'],
        'others_uploads': impact['others_uploads'],
    }
