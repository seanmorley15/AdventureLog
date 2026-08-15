from adventures.models import Location


def user_can_access_location(location: Location, user) -> bool:
    if location.is_public:
        return True

    if user.is_authenticated and location.user == user:
        return True

    if user.is_authenticated:
        for collection in location.collections.all():
            if collection.user == user:
                return True
            if collection.shared_with.filter(uuid=user.uuid).exists():
                return True

    return False
