from datetime import datetime, timezone as dt_timezone

from django.utils import timezone


def _visit_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            value = timezone.make_aware(value, dt_timezone.utc)
        return value.date()
    return value


def is_location_visited(location, user=None):
    """
    Check if a location has been visited by a person, based on its visits.

    A visit counts when it has started and the person travelled on it.
    ``user=None`` means the location's owner.

    Returns:
        bool: True if the person has visited the location, False otherwise
    """
    if user is None:
        user = location.user
    user_id = getattr(user, 'pk', user)
    current_date = timezone.now().date()

    for visit in location.visits.all():
        start_date = _visit_date(visit.start_date)
        if not (start_date and start_date <= current_date):
            continue
        if any(traveler.pk == user_id for traveler in visit.travelers.all()):
            return True

    return False
