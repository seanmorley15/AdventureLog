"""
Day-based trip planning.

A trip stores contiguous ``CollectionItineraryDay`` rows indexed 1..N.
``Collection.start_date`` is the optional anchor; ``end_date`` is derived as the
last projected day. Placements (``CollectionItineraryItem``) sit on a day, in
Ideas (no day, not global), or trip-wide (global notes and checklists).

``convert_collection`` is the single idempotent conversion used by the data
migrations and by backup import. It builds one day per date in the trip, with
no length cap. The other helpers back the itinerary actions and only run
against live models.

Layout, from the bottom up: ``errors``, ``constants`` and ``dates`` have no database
access; ``registry`` says which days a collection has; ``ordering`` and ``spans`` are the
primitives for numbering rows and projecting dates; ``conversion``, ``days``, ``placement``
and ``visits`` are the operations built on them. ``files`` (trails, activities and photos on
a day) and ``legacy`` (date-keyed trips) import the live models, so they are imported by
path rather than from here: the data migrations import this package against historical
models.
"""

from .conversion import apply_type_change, build_days, convert_collection, plan_by_days
from .dates import inclusive_span, local_date, move_to_date, projected_date, shift_datetime
from .days import delete_day, duplicate_day, insert_day, move_day, set_anchor, set_duration, shift_anchor
from .errors import DayPlanError
from .inputs import parse_clock, parse_day_date, parse_flag
from .ordering import compact_bucket
from .placement import move_placement, place_object, reorder_day_plan
from .registry import day_count, get_day, get_day_by_index, indexed_days, is_day_based
from .spans import (
    clear_object_dates,
    shift_object_dates,
    span_bounds,
    sync_projection,
    validate_span,
    write_object_dates,
)
from .visits import log_day, log_visited

__all__ = [
    'DayPlanError', 'apply_type_change', 'build_days', 'clear_object_dates', 'compact_bucket',
    'convert_collection', 'day_count', 'delete_day', 'duplicate_day', 'get_day', 'get_day_by_index',
    'inclusive_span', 'indexed_days', 'insert_day', 'is_day_based', 'local_date', 'log_day',
    'log_visited', 'move_day', 'move_placement', 'move_to_date', 'place_object', 'plan_by_days',
    'parse_clock', 'parse_day_date', 'parse_flag', 'projected_date', 'reorder_day_plan', 'set_anchor', 'set_duration', 'shift_anchor',
    'shift_datetime', 'shift_object_dates', 'span_bounds', 'sync_projection', 'validate_span',
    'write_object_dates',
]
