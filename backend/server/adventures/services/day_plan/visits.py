"""Logging a placed record as a visit."""

from __future__ import annotations

import datetime

from django.db import transaction

from .errors import DayPlanError
from .dates import all_day, local_date, projected_date
from .registry import item_kind
from .spans import span_bounds


def _visit_on_dates(location_id, start, end):
    """An existing visit whose dates overlap this stop. The earliest start wins."""
    from adventures.models import Visit

    match = None
    match_start = None
    for visit in Visit.objects.filter(location_id=location_id):
        visit_start = local_date(visit.start_date, visit.timezone)
        visit_end = local_date(visit.end_date, visit.timezone) or visit_start
        if visit_start is None or visit_end is None:
            continue
        if visit_start <= end and visit_end >= start and (match_start is None or visit_start < match_start):
            match = visit
            match_start = visit_start
    return match

def log_visited(item, visit_date=None):
    """
    Create one visit for a location placement, or return one that already covers it.

    A visit logged earlier on these dates is linked instead of copied. Uses the
    projected date; ``visit_date`` is required when the trip has no anchor or the
    placement is in Ideas. Both visit bounds are always set.
    """
    from adventures.models import Visit

    if item_kind(item) != 'location':
        raise DayPlanError('Only location stops can be logged as visited.')
    if item.logged_visit_id:
        return item.logged_visit, False

    with transaction.atomic():
        anchor = item.collection.start_date
        start_index, end_index = span_bounds(item)
        start_day = projected_date(anchor, start_index) if start_index else None
        end_day = projected_date(anchor, end_index) if end_index else None
        if visit_date is not None:
            span_days = (end_index - start_index) if start_index else 0
            start_day = visit_date
            end_day = visit_date + datetime.timedelta(days=span_days)
        if start_day is None:
            raise DayPlanError('Choose the date you visited.', code='date_required')

        existing = _visit_on_dates(item.object_id, start_day, end_day or start_day)
        if existing is not None:
            item.logged_visit = existing
            item.save(update_fields=['logged_visit', 'updated_at'])
            return existing, False

        visit = Visit.objects.create(
            location_id=item.object_id,
            start_date=all_day(start_day),
            end_date=all_day(end_day or start_day),
            timezone=item.timezone or None,
        )
        item.logged_visit = visit
        item.save(update_fields=['logged_visit', 'updated_at'])
        return visit, True

def log_day(collection, day, visit_date=None):
    """
    Log every non-optional location stop on ``day`` that has no logged visit.

    Day activities are copied onto the visit when the day has one location stop.
    The day activity stays on the day.
    """
    from adventures.models import CollectionItineraryItem
    from .files import promote_ready_activities

    items = CollectionItineraryItem.objects.filter(
        collection=collection,
        day=day,
        is_optional=False,
        logged_visit__isnull=True,
        content_type__model='location',
    ).select_related('day', 'content_type', 'collection').order_by('order')
    pending_activities = False
    from adventures.models import Activity
    if Activity.objects.filter(day=day, promoted_activity__isnull=True).exists():
        pending_activities = True
    if not items and not pending_activities:
        return []
    if collection.start_date is None and visit_date is None and (items or pending_activities):
        raise DayPlanError('Choose the date you visited.', code='date_required')
    logged = []
    with transaction.atomic():
        for item in items:
            visit, _ = log_visited(item, visit_date)
            logged.append(item)
        promote_ready_activities(day, visit_date)
    return logged
