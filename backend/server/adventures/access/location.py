from adventures.access.audience import is_member


def can_read_location(request, location) -> bool:
    """A public place, its owner, or a member of (or guest link to) any collection it is in."""
    if location.is_public:
        return True

    user = request.user
    if user.is_authenticated and location.user_id == user.id:
        return True

    return any(is_member(request, collection) for collection in location.collections.all())
