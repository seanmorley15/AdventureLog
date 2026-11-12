from adventures.access.audience import is_member
from core.visibility import can_read_published


def can_read_location(request, location) -> bool:
    """
    A public place (to signed-in users only while ``ALLOW_PUBLIC_ACCESS`` is off), its owner,
    or a member of (or guest link to) any collection it is in.
    """
    if location.is_public and can_read_published(request.user):
        return True

    user = request.user
    if user.is_authenticated and location.user_id == user.id:
        return True

    return any(is_member(request, collection) for collection in location.collections.all())
