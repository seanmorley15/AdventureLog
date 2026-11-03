"""Forgiving coercion and cleaning for untrusted request values."""

import uuid
from datetime import date, datetime
from urllib.parse import urlparse


def coerce_coordinate(value, min_value, max_value):
    try:
        number = round(float(value), 6)
    except (TypeError, ValueError):
        return None

    if number < min_value or number > max_value:
        return None

    return number


def coerce_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def coerce_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def coerce_bool(value, default=False):
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False

    return default


def clean_url(value):
    if not isinstance(value, str):
        return None

    normalized = value.strip()
    if not normalized:
        return None

    parsed = urlparse(normalized)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return normalized

    return None


def sanitize_tags(raw_tags, max_tags=8):
    if not isinstance(raw_tags, list):
        return []

    tags = []
    for item in raw_tags:
        if not isinstance(item, str):
            continue

        value = item.strip()
        if not value or value in tags:
            continue

        tags.append(value)
        if len(tags) >= max_tags:
            break

    return tags


def sanitize_photo_urls(raw_urls, max_urls=5):
    if not isinstance(raw_urls, list):
        return []

    cleaned = []
    for value in raw_urls:
        url = clean_url(value)
        if not url or url in cleaned:
            continue

        cleaned.append(url)
        if len(cleaned) >= max_urls:
            break

    return cleaned


def parse_iso_date(value):
    """The date in an ISO date or datetime string (or a date), or None if it isn't one."""
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def as_uuid(value):
    """``value`` as a ``uuid.UUID``, or ``None`` when it is not one (an id from a URL, say)."""
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None

