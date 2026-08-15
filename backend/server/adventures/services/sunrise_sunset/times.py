import logging
from datetime import timezone as dt_timezone
from typing import Optional

from django.conf import settings
from django.utils.dateparse import parse_date, parse_datetime

from adventures.providers.sun.sunrisesunset import SunriseSunsetData, fetch_sunrise_sunset
from adventures.services.external_cache import get_or_fetch_cached

logger = logging.getLogger(__name__)

SUNRISE_SUNSET_CACHE_PREFIX = 'sunrise_sunset_v1'
SUNRISE_SUNSET_CACHE_TIMEOUT = getattr(settings, 'SUNRISE_SUNSET_CACHE_TIMEOUT', 60 * 60 * 24 * 30)


def normalize_sunrise_sunset_date(value: str) -> Optional[str]:
    """Normalize an ISO datetime or YYYY-MM-DD string to YYYY-MM-DD."""
    if not value:
        return None

    value = value.strip()
    if len(value) >= 10 and value[4:5] == '-' and value[7:8] == '-':
        parsed_date = parse_date(value[:10])
        if parsed_date:
            return parsed_date.isoformat()

    parsed_datetime = parse_datetime(value)
    if parsed_datetime:
        if parsed_datetime.tzinfo is not None:
            parsed_datetime = parsed_datetime.astimezone(dt_timezone.utc)
        return parsed_datetime.date().isoformat()

    return None


def _cache_key_parts(latitude: float, longitude: float, date_value: str) -> tuple[str, str, str]:
    return (
        f'{latitude:.4f}',
        f'{longitude:.4f}',
        date_value,
    )


def get_sunrise_sunset_for_date(
    latitude: float,
    longitude: float,
    date_value: str,
) -> Optional[SunriseSunsetData]:
    """Return cached sunrise/sunset for a coordinate and calendar date."""
    normalized_date = normalize_sunrise_sunset_date(date_value)
    if not normalized_date:
        return None

    lat_part, lng_part, _ = _cache_key_parts(latitude, longitude, normalized_date)

    def fetch() -> Optional[SunriseSunsetData]:
        result = fetch_sunrise_sunset(latitude, longitude, normalized_date)
        if result.error or not result.data:
            logger.debug('Sunrise/sunset unavailable for %s: %s', normalized_date, result.error)
            return None
        return result.data

    return get_or_fetch_cached(
        SUNRISE_SUNSET_CACHE_PREFIX,
        lat_part,
        lng_part,
        normalized_date,
        fetch_fn=fetch,
        timeout=SUNRISE_SUNSET_CACHE_TIMEOUT,
    )
