"""
The notification inbox: things that happened to a person that they did not do themselves.

Today there is one kind, ``visit_traveler_added``: someone put you on a visit. It is written by the
rules in ``services/travelers.py`` with an explicit ``actor``; no actor means no notification, so
copies made when someone leaves, joining yourself, the owner default, restores and imports stay silent.

Wrap a request that adds people to many visits in ``batch()`` and each person gets one notification
with a count instead of one per visit. The same actor adding the same person to the same visit again
within ``REPEAT_SECONDS`` (say, after removing them) sends no second e-mail; the in-app notification,
which went when they were removed, comes back, so there is never more than one. That memory lives in
the cache, so a server without a shared cache only forgets sooner. Writing never breaks the change it describes, and the e-mail
(only when the server has SMTP) is queued in the same transaction, after the notification, so a queue
error loses the e-mail and not the notification.
"""
from __future__ import annotations

import contextlib
import contextvars
import logging

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from adventures.services.discussion import smtp_configured

logger = logging.getLogger(__name__)

_batch = contextvars.ContextVar('notification_batch', default=None)

# How long the same actor adding the same person to the same visit stays a repeat.
REPEAT_SECONDS = 10 * 60


class _Batch:
    def __init__(self, actor, collection):
        self.actor = actor
        self.collection = collection
        self.added = {}  # user pk -> (user, {visit pk: visit})


@contextlib.contextmanager
def batch(actor, collection=None):
    """
    Collect everyone added to visits inside the block and notify each person once, when it ends
    without an error. Nested blocks join the outer one.
    """
    if _batch.get() is not None:
        yield
        return
    current = _Batch(actor, collection)
    token = _batch.set(current)
    try:
        yield
    finally:
        _batch.reset(token)
    _flush(current)


def travelers_added(visit, users, actor, collection=None):
    """
    Tell ``users`` they were added to ``visit`` by ``actor`` (a user, a request, or None).
    Skips the actor and anyone not a person. Inside ``batch()`` it only collects.
    """
    try:
        if actor is None or not users:
            return
        current = _batch.get()
        if current is not None:
            for user in users:
                current.added.setdefault(user.pk, (user, {}))[1][visit.pk] = visit
            return
        single = _Batch(actor, collection)
        for user in users:
            single.added[user.pk] = (user, {visit.pk: visit})
        _flush(single)
    except Exception:  # pragma: no cover - telling people must never break the change
        logger.exception('Could not notify travelers added to visit %s', getattr(visit, 'pk', None))


def _flush(current):
    from adventures.services.activity_log import actor_for

    try:
        actor_user, actor_name = actor_for(current.actor)
        actor_key = f'user:{actor_user.pk}' if actor_user is not None else None
        if actor_user is None and hasattr(current.actor, 'META'):
            from adventures.services.activity_log import guest_actor

            link = guest_actor(current.actor, current.collection) if current.collection else None
            if link is not None:
                actor_name = link.label or 'Guest'
                actor_key = f'link:{link.pk}'
    except Exception:  # pragma: no cover
        logger.exception('Could not name the actor of a notification')
        return
    for user, visits in current.added.values():
        if actor_user is not None and user.pk == actor_user.pk:
            continue
        visits = list(visits.values())
        fresh, keys = _not_repeats(actor_key, user, visits)
        if _create(user, actor_user, actor_name, visits, current.collection, email=bool(fresh)):
            _remember(keys)


def _repeat_key(actor_key, user, visit):
    return f'traveler-added:{actor_key}:{user.pk}:{visit.pk}'


def _not_repeats(actor_key, user, visits):
    """
    The visits ``user`` was not e-mailed about by this actor in the last ``REPEAT_SECONDS``, and the
    cache keys to remember them by. Without a known actor, or when the cache fails, every visit is new.
    """
    if actor_key is None:
        return visits, {}
    keys = {visit.pk: _repeat_key(actor_key, user, visit) for visit in visits}
    try:
        told = cache.get_many(list(keys.values()))
    except Exception:  # pragma: no cover - a cache outage must not silence anyone
        logger.exception('Could not read the notification repeat cache')
        told = {}
    fresh = [visit for visit in visits if keys[visit.pk] not in told]
    return fresh, {keys[visit.pk]: True for visit in fresh}


def _remember(keys):
    """Remember who was e-mailed once the change is committed (a rolled-back change told nobody)."""
    if not keys:
        return

    def store():
        try:
            cache.set_many(keys, REPEAT_SECONDS)
        except Exception:  # pragma: no cover
            logger.exception('Could not write the notification repeat cache')

    transaction.on_commit(store)


def _create(user, actor_user, actor_name, visits, collection, email=True):
    from adventures.models import Notification

    try:
        # A savepoint, so a database error here cannot poison the change's own transaction.
        with transaction.atomic():
            note = Notification.objects.create(
                user=user,
                kind=Notification.Kind.VISIT_TRAVELER_ADDED,
                actor_user=actor_user,
                actor_name=actor_name[:150],
                data=_visit_data(visits, collection),
            )
    except Exception:
        logger.exception('Could not notify user %s', getattr(user, 'pk', None))
        return False
    if not email:
        return True
    # Its own savepoint, after the row exists: a queue error loses the e-mail, not the notification.
    try:
        with transaction.atomic():
            _queue_email(note, user)
    except Exception:
        logger.exception('Could not queue the e-mail for notification %s', note.pk)
    return True


def _day(value, tz_name):
    from adventures.services.day_plan.dates import local_date

    day = local_date(value, tz_name)
    return day.isoformat() if day else None


def _visit_data(visits, collection):
    visits = sorted(visits, key=lambda v: (v.start_date is None, v.start_date, str(v.pk)))
    locations = {v.location_id for v in visits}
    starts = [d for d in (_day(v.start_date, v.timezone) for v in visits) if d]
    ends = [d for d in (_day(v.end_date or v.start_date, v.timezone) for v in visits) if d]
    first = visits[0]
    data = {
        'count': len(visits),
        'locations': len(locations),
        'start_date': min(starts) if starts else None,
        'end_date': max(ends) if ends else None,
    }
    if collection is not None:
        data['collection_id'] = str(collection.pk)
        data['collection_name'] = collection.name
    if len(visits) == 1:
        data.update({
            'visit_id': str(first.pk),
            'location_id': str(first.location_id),
            'location_name': first.location.name,
        })
    elif len(locations) == 1:
        data.update({'location_id': str(first.location_id), 'location_name': first.location.name})
    return data


def _queue_email(note, user):
    """One e-mail job per notification, only when the server has SMTP and the person has an address."""
    if not smtp_configured() or not user.email:
        return
    from adventures.tasks import send_traveler_added_email_task

    send_traveler_added_email_task.defer(notification_id=str(note.pk), page_url=page_url_for(note))


def page_url_for(note):
    """Where the e-mail sends them: the place for one visit, otherwise the trip."""
    base = getattr(settings, 'FRONTEND_URL', '').rstrip('/') or getattr(settings, 'PUBLIC_URL', '').rstrip('/')
    data = note.data
    if data.get('visit_id') and data.get('location_id'):
        return f'{base}/locations/{data["location_id"]}'
    if data.get('collection_id'):
        return f'{base}/collections/{data["collection_id"]}'
    return base


def _when(data):
    start, end = data.get('start_date'), data.get('end_date')
    if start and end and start != end:
        return f'{start} to {end}'
    return start or ''


def send_traveler_added_email(note, page_url=None, fail_silently=True):
    """E-mail the person a notification is for. A mail error is raised with ``fail_silently=False``, for a job to retry."""
    data = note.data
    who = note.actor_name or 'Someone'
    count = data.get('count', 1)
    when = _when(data)
    if count > 1:
        trip = data.get('collection_name')
        target = f'{count} visits' + (f' on {trip}' if trip else '')
        subject = f'You were added to {target}'
        first = f'{who} added you to {target}.'
    else:
        place = data.get('location_name') or 'a place'
        target = f'a visit at {place}'
        subject = f'You were added to a visit at {place}'
        first = f'{who} added you to {target}' + (f' ({when}).' if when else '.')
    # A name with a line break would make the subject a bad header.
    subject = ' '.join(subject.split())
    lines = [first]
    if count > 1 and when:
        lines.append(f'Dates: {when}.')
    lines += ['']
    if page_url:
        lines += [page_url, '']
    lines.append('If you were not there, you can remove yourself from the visit on that page.')
    return send_mail(
        subject=f'{getattr(settings, "INVITATIONS_EMAIL_SUBJECT_PREFIX", "")}{subject}',
        message='\n'.join(lines),
        from_email=None,
        recipient_list=[note.user.email],
        fail_silently=fail_silently,
    )


def unread_notification_count(user):
    from adventures.models import Notification

    return Notification.objects.filter(user=user, read_at__isnull=True).count()


def mark_read(user, ids=None):
    """Mark the user's own notifications read (all of them, or those in ``ids``). Returns the unread count left."""
    from adventures.models import Notification

    qs = Notification.objects.filter(user=user, read_at__isnull=True)
    if ids is not None:
        qs = qs.filter(pk__in=ids)
    qs.update(read_at=timezone.now())
    return unread_notification_count(user)


def _can_read_location(user, location):
    """``can_read_location`` for an account rather than a request: public, owned, or in a collection they belong to."""
    from adventures.access.audience import is_member
    from core.visibility import can_read_published

    return (
        (location.is_public and can_read_published(user))
        or location.user_id == user.pk
        or any(is_member(user, collection) for collection in location.collections.all())
    )


def serialize_notification(note, user):
    """
    A notification as its recipient sees it. The place and trip names are read again now:
    when the recipient can no longer read the place (or the trip), they are left out.
    """
    from adventures.access.audience import is_member
    from adventures.models import Collection, Location
    from adventures.services.discussion import person_summary

    data = note.data
    location = collection = None
    if data.get('location_id'):
        location = Location.objects.filter(pk=data['location_id']).prefetch_related('collections').first()
        if location is not None and not _can_read_location(user, location):
            location = None
    if data.get('collection_id'):
        collection = Collection.objects.filter(pk=data['collection_id']).first()
        if collection is not None and not is_member(user, collection):
            collection = None
    return {
        'id': str(note.pk),
        'kind': note.kind,
        'actor': {'name': note.actor_name, **person_summary(note.actor_user, user)},
        'visit_id': data.get('visit_id'),  # kept so they can still remove themselves
        'location_id': str(location.pk) if location is not None else None,
        'location_name': location.name if location is not None else '',
        'collection_id': str(collection.pk) if collection is not None else None,
        'collection_name': collection.name if collection is not None else '',
        'count': data.get('count', 1),
        'locations': data.get('locations', 1),
        'start_date': data.get('start_date'),
        'end_date': data.get('end_date'),
        'created_at': note.created_at,
        'read': note.read_at is not None,
    }


def clear_visit_notifications(visit_ids, user_ids=None):
    """
    Delete the single-visit "added you" notifications for these visits and these people, because
    they are off the visit or it is gone. Always pass ``user_ids`` so the recipient index is used
    (``None`` means everyone and scans the table). Summary notifications name no visit and stay.
    Never raises: it must not break the change that triggered it.
    """
    from adventures.models import Notification

    try:
        ids = [str(pk) for pk in visit_ids]
        if user_ids is not None:
            user_ids = list(user_ids)
        if not ids or user_ids == []:
            return
        with transaction.atomic():
            qs = Notification.objects.filter(
                kind=Notification.Kind.VISIT_TRAVELER_ADDED, data__visit_id__in=ids
            )
            if user_ids is not None:
                qs = qs.filter(user_id__in=user_ids)
            qs.delete()
    except Exception:
        logger.exception('Could not clear notifications for visits %s', visit_ids)
