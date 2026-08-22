from __future__ import annotations

from datetime import date, datetime, time, timezone as dt_timezone

from django.utils import timezone


def ensure_aware_utc(value: datetime | None) -> datetime | None:
    """Return a UTC-aware datetime, treating naive values as UTC."""
    if value is None:
        return None
    if timezone.is_naive(value):
        return timezone.make_aware(value, dt_timezone.utc)
    return value


def aware_utc_from_date(value: date, *, end_of_day: bool = False) -> datetime:
    """Build a UTC-aware datetime at the start or end of a calendar day."""
    combined = datetime.combine(value, time.max if end_of_day else time.min)
    return timezone.make_aware(combined, dt_timezone.utc)


def aware_utc_from_date_and_time(value: date, time_value: time) -> datetime:
    """Build a UTC-aware datetime from a date and time."""
    combined = datetime.combine(value, time_value)
    return timezone.make_aware(combined, dt_timezone.utc)


def is_midnight_utc(value: datetime | None) -> bool:
    if value is None:
        return False
    utc_value = ensure_aware_utc(value).astimezone(dt_timezone.utc)
    return utc_value.time() == time.min


def is_end_of_day_utc(value: datetime | None) -> bool:
    if value is None:
        return False
    utc_value = ensure_aware_utc(value).astimezone(dt_timezone.utc)
    return utc_value.time() == time.max


def is_all_day_bound(value: datetime | None) -> bool:
    """True when a datetime is stored as UTC midnight or legacy end-of-day."""
    return is_midnight_utc(value) or is_end_of_day_utc(value)


def normalize_all_day_visit_dates(
    start: datetime | None,
    end: datetime | None,
) -> tuple[datetime | None, datetime | None]:
    """
    Normalize all-day visits to UTC midnight on each calendar date.

    All-day visits always use T00:00:00Z for both start_date and end_date.
    """
    start = ensure_aware_utc(start)
    end = ensure_aware_utc(end)

    if start is None:
        return start, end

    if not is_midnight_utc(start):
        return start, end

    if end is None:
        return start, aware_utc_from_date(start.date())

    if is_all_day_bound(end):
        return start, aware_utc_from_date(end.date())

    return start, end
