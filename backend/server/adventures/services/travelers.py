"""
Who travelled on a visit.

Every visit lists at least one traveler: a new visit without any gets the
location's owner, and the last traveler leaving deletes the visit.

Refusals are ``TravelerError``s with a stable ``code`` (see API.md); this module does not import DRF.
"""
from adventures.services import notifications
from core.errors import ServiceError


class TravelerError(ServiceError):
    """A traveler change that cannot be made. ``code`` says why, ``status`` is the HTTP status."""


def _locked(visit, missing_ok=False):
    """
    The visit row, locked until the surrounding transaction ends, so two people leaving or joining at
    once see each other. Re-read, so a stale instance does not decide. Only the visit row is locked
    (``of=('self',)``), never its location: saving a location locks it first and then its visits, so
    locking both here would invert that order. Gone already: ``not_found``, or None with ``missing_ok``.
    """
    from adventures.models import Visit

    locked = (
        Visit.objects.select_for_update(of=('self',)).select_related('location').filter(pk=visit.pk).first()
    )
    if locked is None and not missing_ok:
        raise TravelerError('This visit no longer exists.', code='not_found', status=404)
    return locked


def ensure_default_traveler(visit):
    """Add the location owner as a traveler when the visit has none."""
    if not visit.travelers.exists():
        visit.travelers.add(visit.location.user_id)


def visited_by(user, now=None):
    """
    Subquery for ``Location.annotate(...)``: a visit that has started (by date, like
    ``is_location_visited``) with this person among its travelers.
    """
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


def _account(requester):
    """The account behind a request or a user, or None (signed out, or a guest link)."""
    user = getattr(requester, 'user', requester)
    return user if user is not None and getattr(user, 'is_authenticated', False) else None


def candidates(location, requester=None, collection=None):
    """
    People who can be named as travelers on a visit to ``location``, as ``requester`` sees it.

    The location's owner always. With ``collection`` (logging from a trip): that trip's owner and
    members. Otherwise the owner and members of the collections holding the location that the
    requester owns or belongs to; the location's owner (and no ``requester``) gets those of every
    collection holding it. So nobody is offered, or can name, someone they share no trip with.
    """
    from django.contrib.auth import get_user_model
    from django.db.models import Q

    from adventures.models import Collection

    people = Q(pk=location.user_id)
    if collection is not None:
        people |= Q(pk=collection.user_id) | Q(shared_with=collection)
    else:
        holding = Collection.objects.filter(locations=location)
        if requester is not None:
            user = _account(requester)
            if user is None:
                holding = holding.none()
            elif user.pk != location.user_id:
                holding = holding.filter(Q(user=user) | Q(shared_with=user))
        holding = holding.values('pk')
        people |= Q(shared_with__in=holding) | Q(collection__in=holding)
    return get_user_model().objects.filter(people).distinct().order_by('username')


def visible_travelers(request, visit):
    """
    The travelers on ``visit`` this request may see, or None when it may see none at all.

    None for anyone signed out and for a guest link (judged by the account, never the link), and
    for someone who neither owns the location, belongs to a collection holding it, nor travelled
    on the visit. The location's owner sees everyone. Anyone else sees the owner, themself, and
    the people they share a collection holding the location with; the rest are left out, so a
    name never reaches someone who shares no trip with that person.

    Reads the loaded ``travelers`` and ``location.collections`` (with ``shared_with``), so a list
    of rows does not query per row.
    """
    user = _account(request)
    if user is None:
        return None
    location = visit.location
    people = list(visit.travelers.all())
    if user.pk == location.user_id:
        return people
    mine = [
        collection for collection in location.collections.all()
        if collection.user_id == user.pk or any(m.pk == user.pk for m in collection.shared_with.all())
    ]
    if not mine and not any(t.pk == user.pk for t in people):
        return None
    seen = {location.user_id, user.pk}
    for collection in mine:
        seen.add(collection.user_id)
        seen.update(m.pk for m in collection.shared_with.all())
    return [t for t in people if t.pk in seen]


def can_see_travelers(request, visit):
    """Whether this request may see any of the visit's travelers (see ``visible_travelers``)."""
    return visible_travelers(request, visit) is not None


def set_travelers(visit, users, actor, fresh=False, collection=None):
    """
    Make ``users`` the visit's travelers.

    Everyone newly added who is not ``actor`` is told (see ``services/notifications``). ``fresh``
    says the visit was just created, so the owner default it starts with does not count as
    someone already there.

    Everyone added must be a candidate for ``actor`` (``candidates``; within ``collection`` when
    logging from a trip), or ``traveler_not_allowed``. Travelers who are not candidates for them
    (they left the trip, or are on another trip ``actor`` is not on) stay on the visit untouched:
    only they can remove themselves.
    A visit always keeps at least one traveler: a result with nobody is ``traveler_required``.
    """
    wanted = {user.pk: user for user in users}
    existing = {user.pk: user for user in visit.travelers.all()}
    allowed = set(candidates(visit.location, actor, collection).values_list('pk', flat=True))
    if any(pk not in allowed and pk not in existing for pk in wanted):
        raise TravelerError('Travelers must be the owner or members of the location.', code='traveler_not_allowed')
    keep = {pk: user for pk, user in existing.items() if pk not in allowed}
    final = [*wanted.values(), *keep.values()]
    if not final:
        raise TravelerError('A visit needs at least one traveler.', code='traveler_required')
    already = set() if fresh else set(existing)
    visit.travelers.set(final)
    mark_regions_for_travelers(visit.location)
    notifications.travelers_added(visit, [u for pk, u in wanted.items() if pk not in already], actor, collection)


def add_travelers(visit, users, actor=None, collection=None):
    """
    Add ``users`` to the visit's travelers, keeping the ones already there. Each must be a candidate
    for ``actor`` (within ``collection`` when given).
    Those who were not there and are not ``actor`` are told; without an ``actor`` nobody is.
    """
    wanted = {user.pk: user for user in users}
    allowed = set(candidates(visit.location, actor, collection).values_list('pk', flat=True))
    if any(pk not in allowed for pk in wanted):
        raise TravelerError('Travelers must be the owner or members of the location.', code='traveler_not_allowed')
    if wanted:
        already = set(visit.travelers.filter(pk__in=wanted).values_list('pk', flat=True))
        visit.travelers.add(*wanted.values())
        mark_regions_for_travelers(visit.location)
        notifications.travelers_added(
            visit, [u for pk, u in wanted.items() if pk not in already], actor, collection
        )


def join(visit, user):
    """
    Add the user as a traveler. Only people who reach the location (its owner, or the owner or a
    member of a collection holding it) may join (403 ``permission_denied``).
    """
    from django.db import transaction

    if not candidates(visit.location, user).filter(pk=user.pk).exists():
        raise TravelerError('You cannot join this visit.', code='permission_denied', status=403)
    with transaction.atomic():
        visit = _locked(visit)
        visit.travelers.add(user)
        mark_regions_for_travelers(visit.location)


def leave(visit, user):
    """
    Remove the user as a traveler. Deletes the visit and returns True when nobody is left.
    Someone who was not a traveler changes nothing.
    """
    from django.db import transaction

    with transaction.atomic():
        return _leave_locked(_locked(visit), user)


def _leave_locked(visit, user):
    """``leave`` on a visit row this transaction has already locked."""
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

    - A traveler is taken off the visit, and the visit goes with them when they were the last
      traveler (``'deleted'``), else it stays for the others (``'detached'``). Activities and
      photos stay with a visit that is only detached from.
    - ``for_everyone``: the location's owner deletes it for everyone. Anyone else gets a 403
      ``permission_denied``.
    - The location's owner who is not on it deletes a visit nobody travelled on; one that others
      travelled on is a 409 ``visit_has_travelers`` (use ``for_everyone``).
    - Anyone else who is not on it gets a 403 ``not_a_traveler``: a visit others travelled on is
      theirs to keep.
    """
    from django.db import transaction

    with transaction.atomic():
        return _remove_or_delete_locked(_locked(visit), user, for_everyone)


def _remove_or_delete_locked(visit, user, for_everyone=False):
    """``remove_or_delete`` on a visit row this transaction has already locked."""
    is_owner = user.pk == visit.location.user_id
    if for_everyone:
        if not is_owner:
            raise TravelerError(
                'Only the location owner can delete a visit for everyone.', code='permission_denied', status=403
            )
        visit.delete()
        return 'deleted'
    if visit.travelers.filter(pk=user.pk).exists():
        return 'deleted' if _leave_locked(visit, user) else 'detached'
    if is_owner and not visit.travelers.exists():
        # A visit nobody travelled on (left over from before this rule) is the owner's to clear.
        visit.delete()
        return 'deleted'
    if is_owner:
        raise TravelerError(
            'Other people travelled on this visit. Delete it for everyone (for_everyone=1) to remove it.',
            code='visit_has_travelers', status=409,
        )
    raise TravelerError(
        'Only the location owner or someone who travelled can remove this visit.',
        code='not_a_traveler', status=403,
    )


def detach_if_traveler(visit, user):
    """
    ``remove_or_delete`` for someone who may not be on the visit, where that is no reason to refuse
    (removing a stop, saving a location's visit list, and the internal paths that take someone off
    visits they read earlier: copies, leaving, account deletion). A visit they are not on (any more)
    is left as it is (``'kept'``), and one already deleted counts as done (``'deleted'``). The
    location's owner still clears a visit nobody travelled on. Locks the row once.
    """
    from django.db import transaction

    with transaction.atomic():
        visit = _locked(visit, missing_ok=True)
        if visit is None:
            return 'deleted'
        on_it = visit.travelers.filter(pk=user.pk).exists()
        if on_it or (user.pk == visit.location.user_id and not visit.travelers.exists()):
            return _remove_or_delete_locked(visit, user)
        return 'kept'


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


def _trip_gains(collection, users):
    """
    The visits of the trip (``trip_visits``) that would gain someone in ``users``, and the
    ``{'visits': n, 'locations': n}`` count of them. Each of ``users`` must be the owner or a
    member of the trip, or ``traveler_not_allowed`` is raised.
    """
    wanted = {user.pk for user in users}
    allowed = {collection.user_id, *collection.shared_with.values_list('pk', flat=True)}
    if any(pk not in allowed for pk in wanted):
        raise TravelerError('Everyone must be the owner or a member of this collection.', code='traveler_not_allowed')

    visits = list(trip_visits(collection).select_related('location').prefetch_related('travelers'))
    gaining = [v for v in visits if not wanted <= {t.pk for t in v.travelers.all()}]
    return gaining, {'visits': len(gaining), 'locations': len({v.location_id for v in gaining})}


def add_to_trip_preview(collection, users):
    """What ``add_to_trip`` would do, changing nothing: ``{'visits': n, 'locations': n}``."""
    return _trip_gains(collection, users)[1]


def add_to_trip(collection, users, actor=None):
    """
    Add ``users`` to the trip's visits (see ``trip_visits``). Each must be the owner or a member
    of the trip, or ``traveler_not_allowed`` is raised and nothing changes.

    Returns ``{'visits': n, 'locations': n}``: the visits that gained someone and their distinct
    locations. A visit that already has all of them counts for nothing. A ``CollectionActivity``
    is recorded when anything changed. It holds counts only (``people``, ``visits``,
    ``locations``), never names: editor guest links read the feed.
    """
    from django.db import transaction

    gaining, result = _trip_gains(collection, users)
    if not gaining:
        return result
    wanted = {user.pk: user for user in users}
    with transaction.atomic(), notifications.batch(actor, collection):
        for visit in gaining:
            add_travelers(visit, wanted.values(), actor, collection)
        if actor is not None:
            from adventures.models import CollectionActivity
            from adventures.services.activity_log import record_activity

            record_activity(
                collection, actor, CollectionActivity.Verb.TRAVELERS_ADDED,
                people=len(wanted), **result,
            )
    return result


def take_my_visits(original, user, collection=None):
    """
    Give ``user`` their own copy of a location they travelled to but don't own.

    The copy keeps the original's name and gets a copy of each visit they travelled on (dates,
    timezone and notes), with them as its only traveler. They are then removed from the original
    visits (see ``detach_if_traveler``), so nothing is counted twice. The photos, attachments and
    activities they added to those visits are copied too (``copy_visit_uploads``), sharing the
    stored files, so deleting either side never removes the other's; other people's stay behind.
    The originals are left as they are. With ``collection`` the copy goes in that collection, as
    ``copy_location`` does. All or nothing. The owner of the location gets ``location_already_yours``:
    it is already theirs. Someone on none of its visits gets ``no_visits_to_take``.
    """
    from django.db import transaction

    from adventures.models import Visit
    from adventures.services.locations import copy as copying

    if original.user_id == user.pk:
        raise TravelerError('This location is already yours.', code='location_already_yours')
    with transaction.atomic():
        mine = list(original.visits.filter(travelers=user).order_by('start_date', 'created_at'))
        if not mine:
            raise TravelerError('You are not a traveler on any visit to this location.', code='no_visits_to_take')
        copy = copying.copy_location(original, user, collection=collection, name=original.name)
        for visit in mine:
            moved = Visit.objects.create(
                location=copy, start_date=visit.start_date, end_date=visit.end_date,
                timezone=visit.timezone, notes=visit.notes,
            )
            moved.travelers.set([user])
            copying.copy_visit_uploads(visit, moved, user)
        for visit in mine:
            # Read before the copy was made: someone may have taken them off meanwhile.
            detach_if_traveler(visit, user)
        mark_regions_for_travelers(copy)
    return copy


def _places_lost(collections, user):
    """
    Locations in ``collections`` that ``user`` travelled to and would no longer reach without all
    of them: not their own, and in no other collection they own or belong to. The same rule as
    ``lost_access_users``, from the person's side.
    """
    from django.db.models import Exists, OuterRef, Q

    from adventures.models import Collection, Location

    ids = [c.pk for c in collections]
    reachable = (
        Collection.objects.filter(locations=OuterRef('pk')).exclude(pk__in=ids)
        .filter(Q(user=user) | Q(shared_with=user))
    )
    return (
        Location.objects.filter(collections__in=ids, visits__travelers=user)
        .exclude(user=user).exclude(Exists(reachable)).distinct()
    )


def member_locations(collection, user):
    """
    Locations in the collection that ``user`` doesn't own, travelled to and reaches through no other
    collection: what leaving takes from them (``lost_access_users`` with the collection ignored).
    """
    return _places_lost([collection], user)


def _uploads_on(visits, mine):
    """
    Photos, attachments and activities on ``visits`` (a queryset of pks) added by anyone not in
    ``mine``, with the photos on those activities.
    """
    from django.contrib.contenttypes.models import ContentType

    from adventures.models import Activity, ContentAttachment, ContentImage

    activities = Activity.objects.filter(visit__in=visits)
    visit_type = ContentType.objects.get_for_model(visits.model)
    activity_type = ContentType.objects.get_for_model(Activity)
    return (
        ContentImage.objects.filter(content_type=visit_type, object_id__in=visits).exclude(user__in=mine).count()
        + ContentAttachment.objects.filter(content_type=visit_type, object_id__in=visits).exclude(user__in=mine).count()
        + activities.exclude(user__in=mine).count()
        + ContentImage.objects.filter(content_type=activity_type, object_id__in=activities.values('pk'))
        .exclude(user__in=mine).count()
    )


def _visits_that_would_go(locations, leaving):
    """
    Visits at ``locations`` that only people in ``leaving`` (user pks) travelled on: taking them
    off deletes the visit.
    """
    from django.contrib.auth import get_user_model

    from adventures.models import Visit

    staying = get_user_model().objects.exclude(pk__in=leaving)
    shared = Visit.objects.filter(travelers__in=staying).values('pk')
    return Visit.objects.filter(location__in=locations, travelers__in=leaving).exclude(pk__in=shared).distinct()


def _leave_impact(locations, user):
    """``{locations, others_uploads}`` for ``user`` being taken off visits at ``locations``."""
    doomed = _visits_that_would_go(locations, [user.pk]).values('pk')
    return {
        'locations': locations.count(),
        'visits_deleted': doomed.count(),
        'others_uploads': _uploads_on(doomed, [user]),
    }


def leave_preview(collection, user):
    """
    What leaving (or being removed from) the collection would do, without changing anything.

    ``locations``: the locations it takes from ``user`` (see ``member_locations``), each one
    copied when copies are kept. ``others_uploads``: the photos, attachments and activities
    that other people added to visits ``user`` is the only traveler on. Those visits are
    deleted either way, so these go with them, as do other people's photos of activities on them.
    """
    impact = _leave_impact(member_locations(collection, user), user)
    return {'locations': impact['locations'], 'others_uploads': impact['others_uploads']}


def leave_preview_all(collections, user):
    """
    ``leave_preview`` for leaving several collections at once (going private), judging each place
    against all of them together and counting a place held by more than one a single time. Also
    says ``visits_deleted``.
    """
    return _leave_impact(_places_lost(list(collections), user), user)


def leave_preview_all_places(locations, user):
    """``{locations, visits_deleted, others_uploads}`` for ``user`` coming off the visits at ``locations``."""
    return _leave_impact(locations, user)


def release_member(collection, user, keep_copies):
    """
    Take ``user``'s history out of the collection before they leave it (see ``member_locations``).

    With ``keep_copies`` each of those locations is copied to their account with their visits
    (``take_my_visits``); otherwise they are only removed from its visits. Either way they end
    up on none of the location's visits, whichever trip a visit was part of. A visit left with
    nobody is deleted. Places they still reach through another collection, and places they own,
    are untouched. Region and city credit already marked for them stays. All or nothing. Returns
    the number of locations copied.
    """
    return release_member_all([collection], user, keep_copies)


def release_member_all(collections, user, keep_copies):
    """``release_member`` for leaving all of ``collections`` at once, each place judged against all of them."""
    from django.db import transaction

    from adventures.models import Visit

    copied = 0
    with transaction.atomic():
        for location in list(_places_lost(list(collections), user).order_by('name', 'pk')):
            if keep_copies:
                take_my_visits(location, user)
                copied += 1
            else:
                for visit in list(Visit.objects.filter(location=location, travelers=user)):
                    detach_if_traveler(visit, user)
    return copied


def lost_access_users(location, ignoring=()):
    """
    People on ``location``'s visits who don't own it and, leaving out the collections in
    ``ignoring``, neither own nor belong to any collection that holds it.
    """
    from django.contrib.auth import get_user_model
    from django.db.models import Exists, OuterRef, Q

    from adventures.models import Collection

    reachable = Collection.objects.filter(locations=location).exclude(pk__in=[c.pk for c in ignoring]).filter(
        Q(user=OuterRef('pk')) | Q(shared_with=OuterRef('pk'))
    )
    return (
        get_user_model().objects.filter(visits_traveled__location=location)
        .exclude(pk=location.user_id)
        .exclude(Exists(reachable))
        .distinct()
    )


def release_lost_access(location, ignoring=()):
    """
    Treat everyone who can no longer reach ``location`` as removed from its trip: they come off
    its visits and get their own copy with their visits (``take_my_visits``). Call it when the
    place is about to leave, or has left, the collections in ``ignoring``. Safe to repeat: once
    released nobody is left on the visits. Returns how many people were released.
    """
    from django.db import transaction

    with transaction.atomic():
        users = list(lost_access_users(location, ignoring).order_by('pk'))
        for user in users:
            take_my_visits(location, user)
    return len(users)


def lost_access_plan(locations, ignoring=(), exclude=None):
    """
    ``[(location, [users])]``: who ``lost_access_users`` finds at each of ``locations``, leaving out
    places where it is nobody. ``exclude`` is a user who is going too (a deleted account): never planned.
    """
    plan = []
    for location in locations:
        found = lost_access_users(location, ignoring)
        if exclude is not None:
            found = found.exclude(pk=exclude.pk)
        users = list(found.order_by('pk'))
        if users:
            plan.append((location, users))
    return plan


def collections_release_plan(collections, exclude=None):
    """
    ``lost_access_plan`` for the places of ``collections`` that are about to go with all of
    them at once, so a place held by two of them is judged once, against the collections that
    remain. Only places that someone other than the owner travelled to are looked at.
    """
    from django.db.models import Exists, OuterRef

    from adventures.models import Location, Visit

    collections = list(collections)
    through = Visit.travelers.through
    user_field = Visit.travelers.field.m2m_reverse_name()
    others = through.objects.filter(visit__location=OuterRef('pk')).exclude(
        **{user_field: OuterRef('user_id')}
    )
    places = Location.objects.filter(collections__in=collections).filter(Exists(others)).distinct()
    return lost_access_plan(places, ignoring=collections, exclude=exclude)


def release_preview(plan):
    """
    What carrying out a ``lost_access_plan`` would do, without changing anything.

    ``people``: everyone who would get a copy. ``places``: the places that would be copied.
    ``visits_deleted``: visits only released people travelled on, which go with the original
    place. ``others_uploads``: what people who are not released added to those visits.
    """
    people, places, visits_deleted, others_uploads = {}, 0, 0, 0
    for location, users in plan:
        places += 1
        people.update({user.pk: user for user in users})
        doomed = _visits_that_would_go([location], [user.pk for user in users]).values('pk')
        visits_deleted += doomed.count()
        others_uploads += _uploads_on(doomed, users)
    return {
        'people': sorted(people.values(), key=lambda user: user.username),
        'places': places,
        'visits_deleted': visits_deleted,
        'others_uploads': others_uploads,
    }


def release_summary(plan, viewer):
    """
    ``release_preview`` as the unlink and collection-deletion previews answer it: the people
    released (``people_released``), whether ``viewer`` is one of them (``includes_you``), and
    ``visits_deleted``, ``others_uploads`` and ``places``.
    """
    preview = release_preview(plan)
    return {
        'people_released': preview['people'],
        'includes_you': any(user.pk == viewer.pk for user in preview['people']),
        'visits_deleted': preview['visits_deleted'],
        'others_uploads': preview['others_uploads'],
        'places': preview['places'],
    }


def release_collections_travelers(collections, exclude=None):
    """
    Before ``collections`` are all deleted, give the lost-access travelers of their places
    their copies (``release_lost_access`` with every one of them ignored at once, so a place
    held by two of them is judged once, against the collections that remain). Only places
    that someone other than the owner travelled to are looked at. Returns how many people
    were released.
    """
    from django.db import transaction

    released = 0
    with transaction.atomic():
        for location, users in collections_release_plan(collections, exclude):
            for user in users:
                take_my_visits(location, user)
            released += len(users)
    return released


def release_collection_travelers(collection):
    """``release_collections_travelers`` for one collection about to be deleted."""
    return release_collections_travelers([collection])


def creator_may_delete(location, user):
    """
    Whether ``user``, who added ``location`` to someone else's trip, may delete the place itself.

    Only while it is theirs alone in practice: they are still an editor of the one collection
    holding it, nobody else travelled to it, and nobody else added a photo, attachment, activity
    or trail. Then deleting it takes nothing from anyone and leaves the owner nothing stray.
    """
    from django.contrib.contenttypes.models import ContentType

    from adventures.access.audience import EDITOR, member_role
    from adventures.models import ContentAttachment, ContentImage, Visit

    if (
        user is None or not getattr(user, 'is_authenticated', False)
        or location.created_by_id != user.id or location.user_id == user.id
    ):
        return False
    collections = list(location.collections.all()[:2])
    if len(collections) != 1 or member_role(collections[0], user) != EDITOR:
        return False
    visits = location.visits.all()
    if Visit.travelers.through.objects.filter(visit__in=visits).exclude(customuser_id=user.id).exists():
        return False
    if location.trails.exists() or _uploads_on(visits.values('pk'), [user]):
        return False
    location_type = ContentType.objects.get_for_model(location)
    return not (
        ContentImage.objects.filter(content_type=location_type, object_id=location.pk).exclude(user=user).exists()
        or ContentAttachment.objects.filter(content_type=location_type, object_id=location.pk).exclude(user=user).exists()
    )
