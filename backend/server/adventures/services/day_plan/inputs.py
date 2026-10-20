"""Reading day-plan values out of a request. Each raises DayPlanError when the value is unusable."""

from django.utils.dateparse import parse_date, parse_time

from .errors import DayPlanError


def parse_flag(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('1', 'true', 'yes', 'y', 't')


def parse_day_date(value):
    if value in (None, ''):
        return None
    parsed = parse_date(str(value).split('T')[0])
    if parsed is None:
        raise DayPlanError('Use a YYYY-MM-DD date.')
    return parsed


def parse_clock(value):
    if value in (None, ''):
        return None
    parsed = parse_time(str(value))
    if parsed is None:
        raise DayPlanError('Use an HH:MM time.')
    return parsed
