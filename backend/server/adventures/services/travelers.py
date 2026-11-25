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
    """Subquery for ``Location.annotate(...)``: a visit that has started (by date, like ``is_location_visited``) with this person among its travelers."""
    from django.db.models import Exists, OuterRef
    from django.utils import timezone

    from adventures.models import Visit

    return Exists(
        Visit.objects.filter(
            location_id=OuterRef('pk'),
            start_date__date__lte=(now or timezone.now()).date(),
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
        Visit.objects.filter(location_id=location.pk, start_date__date__lte=timezone.now().date())
        .values_list('travelers', flat=True)
    )
    user_ids.discard(None)
    for user_id in user_ids:
        if location.region_id:
            mark_regions_visited(user_id, [location.region_id])
        if location.city_id:
            mark_cities_visited(user_id, [location.city_id])


def candidates(location):
    """People who can be named as travelers: the location's owner, plus the owner and members of each collection holding it."""
    from django.contrib.auth import get_user_model
    from django.db.models import Q

    return get_user_model().objects.filter(
        Q(pk=location.user_id)
        | Q(shared_with__locations=location)
        | Q(collection__locations=location)
    ).distinct().order_by('username')


def can_see_travelers(request, visit):
    """
    Whether this request may see who travelled on the visit: the location's owner, a member
    of a collection holding the location, or a traveler. Never anonymous, and never a guest
    link (a guest link is not an account, so it is not treated as membership here).
    """
    from adventures.access.audience import is_member

    user = getattr(request, 'user', None)
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    location = visit.location
    if user.pk == location.user_id:
        return True
    if any(t.pk == user.pk for t in visit.travelers.all()):
        return True
    # Pass the user, not the request, so a guest token never counts as membership.
    return any(is_member(user, collection) for collection in location.collections.all())


def set_travelers(visit, users, actor):
    """
    Make ``users`` the visit's travelers.

    Everyone added must be a candidate, or ``ValidationError`` is raised. Travelers who are no
    longer candidates (they left the trip) stay on the visit: only they can remove themselves.
    A visit always keeps at least one traveler: a result with nobody is refused.
    """
    from rest_framework.exceptions import ValidationError

    wanted = {user.pk: user for user in users}
    existing = {user.pk: user for user in visit.travelers.all()}
    allowed = set(candidates(visit.location).values_list('pk', flat=True))
    if any(pk not in allowed and pk not in existing for pk in wanted):
        raise ValidationError({'traveler_uuids': 'Travelers must be the owner or members of the location.'})
    keep = {pk: user for pk, user in existing.items() if pk not in allowed}
    final = [*wanted.values(), *keep.values()]
    if not final:
        raise ValidationError({'traveler_uuids': 'A visit needs at least one traveler.'})
    visit.travelers.set(final)
    mark_regions_for_travelers(visit.location)


def add_travelers(visit, users):
    """Add ``users`` to the visit's travelers, keeping the ones already there. Each must be a candidate."""
    from rest_framework.exceptions import ValidationError

    wanted = {user.pk: user for user in users}
    allowed = set(candidates(visit.location).values_list('pk', flat=True))
    if any(pk not in allowed for pk in wanted):
        raise ValidationError({'traveler_uuids': 'Travelers must be the owner or members of the location.'})
    if wanted:
        visit.travelers.add(*wanted.values())
        mark_regions_for_travelers(visit.location)


def join(visit, user):
    """Add the user as a traveler. Only candidates may join."""
    from rest_framework.exceptions import PermissionDenied

    if not candidates(visit.location).filter(pk=user.pk).exists():
        raise PermissionDenied('You cannot join this visit.')
    visit.travelers.add(user)
    mark_regions_for_travelers(visit.location)


def leave(visit, user):
    """
    Remove the user as a traveler. Deletes the visit and returns True when nobody is left.
    Someone who was not a traveler changes nothing.
    """
    if not visit.travelers.filter(pk=user.pk).exists():
        return False
    visit.travelers.remove(user)
    if visit.travelers.exists():
        return False
    visit.delete()
    return True


def remove_or_delete(visit, user, for_everyone=False):
    """
    Delete a visit on behalf of ``user``. Returns ``'deleted'`` or ``'detached'``.

    Only the location's owner may delete for everyone (anyone else gets ``PermissionDenied``).
    Otherwise the user is removed from the visit, and the visit goes with them when they were
    the last traveler. Someone who was not a traveler changes nothing and gets ``'detached'``:
    a visit others travelled on is theirs to keep. Activities and photos stay with a visit that
    is only detached from.
    """
    from rest_framework.exceptions import PermissionDenied

    if for_everyone:
        if user.pk != visit.location.user_id:
            raise PermissionDenied('Only the location owner can delete a visit for everyone.')
        visit.delete()
        return 'deleted'
    return 'deleted' if leave(visit, user) else 'detached'


def trip_visits(collection):
    """
    The visits that belong to a trip: the ones its itinerary logged, plus, when the trip has
    dates, visits to its locations that started on those days (inclusive, by date). An undated
    trip owns only the visits it logged, so an earlier visit to the same place stays out.
    """
    from django.db.models import Q

    from adventures.models import Visit

    belongs = Q(pk__in=collection.itinerary_items.filter(logged_visit__isnull=False).values('logged_visit_id'))
    if collection.start_date and collection.end_date:
        belongs |= Q(
            location__collections=collection,
            start_date__date__gte=collection.start_date,
            start_date__date__lte=collection.end_date,
        )
    return Visit.objects.filter(belongs).distinct()


def add_to_trip(collection, users, dry_run=False, actor=None):
    """
    Add ``users`` to the trip's visits (see ``trip_visits``). Each must be the owner or a member
    of the trip, or ``ValidationError`` is raised and nothing changes.

    Returns ``{'visits': n, 'locations': n}``: the visits that gained someone and their distinct
    locations. A visit that already has all of them counts for nothing. A dry run only counts.
    Otherwise a ``CollectionActivity`` is recorded when anything changed.
    """
    from django.db import transaction
    from rest_framework.exceptions import ValidationError

    wanted = {user.pk: user for user in users}
    allowed = {collection.user_id, *collection.shared_with.values_list('pk', flat=True)}
    if any(pk not in allowed for pk in wanted):
        raise ValidationError({'user_uuids': 'Everyone must be the owner or a member of this collection.'})

    visits = list(trip_visits(collection).select_related('location').prefetch_related('travelers'))
    gaining = [v for v in visits if not wanted.keys() <= {t.pk for t in v.travelers.all()}]
    result = {'visits': len(gaining), 'locations': len({v.location_id for v in gaining})}
    if dry_run or not gaining:
        return result
    with transaction.atomic():
        for visit in gaining:
            add_travelers(visit, wanted.values())
        if actor is not None:
            from adventures.models import CollectionActivity
            from adventures.services.activity_log import record_activity

            record_activity(
                collection, actor, CollectionActivity.Verb.TRAVELERS_ADDED,
                usernames=sorted(user.username for user in wanted.values()), **result,
            )
    return result
