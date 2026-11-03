"""Date and timezone arithmetic for a day-based trip. No database access."""

from __future__ import annotations

import datetime
from typing import Iterable



def _tzinfo(name):
    from zoneinfo import ZoneInfo

    try:
        return ZoneInfo(name) if name else datetime.timezone.utc
    except Exception:
        return datetime.timezone.utc

def _is_all_day(value):
    utc_value = value.astimezone(datetime.timezone.utc)
    return utc_value.time() in (datetime.time.min, datetime.time.max)

def local_date(value, tz_name=None):
    """Calendar date of a stored datetime. UTC midnight is a date-only value."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        if _is_all_day(value):
            return value.astimezone(datetime.timezone.utc).date()
        return value.astimezone(_tzinfo(tz_name)).date()
    return value

def all_day(day):
    return datetime.datetime.combine(day, datetime.time.min, tzinfo=datetime.timezone.utc)

def move_to_date(existing, new_day, tz_name=None, fallback_time=None):
    """Put ``new_day`` on a datetime, keeping the clock time it already had."""
    if existing is not None:
        if existing.tzinfo is None:
            existing = existing.replace(tzinfo=datetime.timezone.utc)
        if _is_all_day(existing):
            return all_day(new_day)
        tz = _tzinfo(tz_name)
        local_time = existing.astimezone(tz).time()
        return datetime.datetime.combine(new_day, local_time, tzinfo=tz).astimezone(datetime.timezone.utc)
    if fallback_time is not None:
        tz = _tzinfo(tz_name)
        return datetime.datetime.combine(new_day, fallback_time, tzinfo=tz).astimezone(datetime.timezone.utc)
    return all_day(new_day)

def shift_datetime(value, days, tz_name=None):
    """
    Move a stored datetime by ``days`` civil days, keeping its local clock face.

    The local wall time in ``tz_name`` is kept across DST changes; an ambiguous
    fall-back hour takes the first offset. UTC midnight stays a date-only value.
    """
    if value is None or not days:
        return value
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.timezone.utc)
    if _is_all_day(value):
        return value + datetime.timedelta(days=days)
    tz = _tzinfo(tz_name)
    local = value.astimezone(tz).replace(tzinfo=None) + datetime.timedelta(days=days)
    return local.replace(tzinfo=tz, fold=0).astimezone(datetime.timezone.utc)

def projected_date(anchor, index):
    if anchor is None or index is None:
        return None
    return anchor + datetime.timedelta(days=index - 1)

def inclusive_span(start, end):
    if not start or not end:
        return None
    return (end - start).days + 1

def contiguous_runs(indexes: Iterable[int]):
    values = sorted(set(indexes))
    runs = []
    for value in values:
        if runs and value == runs[-1][1] + 1:
            runs[-1][1] = value
        else:
            runs.append([value, value])
    return [(start, end) for start, end in runs]

def _date_range(start, end):
    current = start
    while current <= end:
        yield current
        current += datetime.timedelta(days=1)
