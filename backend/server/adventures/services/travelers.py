"""
Who travelled on a visit.

Every visit lists its travelers. A visit with no travelers counts for the
owner of its location, so existing data and newly created visits keep working
without any extra input.
"""


def ensure_default_traveler(visit):
    """Add the location owner as a traveler when the visit has none."""
    if not visit.travelers.exists():
        visit.travelers.add(visit.location.user_id)


def visited_by(user, now=None):
    """Subquery for ``Location.annotate(...)``: a started visit with this person among its travelers."""
    from django.db.models import Exists, OuterRef
    from django.utils import timezone

    from adventures.models import Visit

    return Exists(
        Visit.objects.filter(
            location_id=OuterRef('pk'),
            start_date__lte=now or timezone.now(),
            travelers=user,
        )
    )


def perspective_user(request, location):
    """
    The person whose visited status to show for a location.

    The requester when they own the location, belong to a collection holding
    it, or travelled on one of its visits. Everyone else sees the owner's.
    """
    user = getattr(request, 'user', None)
    if user is None or not getattr(user, 'is_authenticated', False):
        return location.user
    if user.pk == location.user_id:
        return user
    # Read from the loaded collections and their members, so a list of rows does not query per row.
    if any(
        collection.user_id == user.pk or any(m.pk == user.pk for m in collection.shared_with.all())
        for collection in location.collections.all()
    ):
        return user
    if any(t.pk == user.pk for visit in location.visits.all() for t in visit.travelers.all()):
        return user
    return location.user


def where_ive_been_q(user):
    """Locations this person travelled to while they owned them or belonged to their collection. Add ``.distinct()``."""
    from django.db.models import Q

    return Q(user=user) | (
        Q(visits__travelers=user) & (Q(collections__shared_with=user) | Q(collections__user=user))
    )


def mark_regions_for_travelers(location):
    """Mark the location's region and city as visited for everyone who travelled on a started visit."""
    from django.utils import timezone

    from adventures.models import Visit
    from worldtravel.services import mark_cities_visited, mark_regions_visited

    if not (location.region_id or location.city_id):
        return
    user_ids = set(
        Visit.objects.filter(location_id=location.pk, start_date__lte=timezone.now())
        .values_list('travelers', flat=True)
    )
    user_ids.discard(None)
    for user_id in user_ids:
        if location.region_id:
            mark_regions_visited(user_id, [location.region_id])
        if location.city_id:
            mark_cities_visited(user_id, [location.city_id])
