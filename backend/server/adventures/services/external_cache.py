import hashlib
import logging
import re
from typing import Callable, Optional, TypeVar

from django.conf import settings
from django.core.cache import cache
from django.core.cache.backends.base import InvalidCacheKey

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Memcached rejects whitespace and control characters. Keep keys URL/token-safe.
_UNSAFE_CACHE_CHARS = re.compile(r'[^A-Za-z0-9._-]+')


def build_cache_key(prefix: str, *parts: str) -> str:
    sanitized_parts = [
        _UNSAFE_CACHE_CHARS.sub('_', (part or '').strip().lower()).strip('_')
        for part in parts
    ]
    normalized = ':'.join(part for part in sanitized_parts if part)
    key = f'{prefix}:{normalized}' if normalized else prefix
    if len(key) > 200:
        digest = hashlib.sha256(f'{prefix}:{normalized}'.encode()).hexdigest()
        return f'{prefix}:{digest}'
    return key


def get_cached(prefix: str, *parts: str) -> Optional[T]:
    try:
        return cache.get(build_cache_key(prefix, *parts))
    except InvalidCacheKey:
        logger.warning('Skipping invalid cache key for prefix %s', prefix)
        return None


def set_cached(prefix: str, *parts: str, value: T, timeout: Optional[int] = None) -> T:
    try:
        cache.set(
            build_cache_key(prefix, *parts),
            value,
            timeout or getattr(settings, 'EXTERNAL_API_CACHE_TIMEOUT', 60 * 60 * 24),
        )
    except InvalidCacheKey:
        logger.warning('Unable to store cache key for prefix %s', prefix)
    return value


def get_or_fetch_cached(
    prefix: str,
    *parts: str,
    fetch_fn: Callable[[], Optional[T]],
    timeout: Optional[int] = None,
) -> Optional[T]:
    cached = get_cached(prefix, *parts)
    if cached is not None:
        return cached

    value = fetch_fn()
    if value is not None:
        set_cached(prefix, *parts, value=value, timeout=timeout)
    return value
