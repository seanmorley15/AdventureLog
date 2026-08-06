import hashlib
from typing import Callable, Optional, TypeVar

from django.conf import settings
from django.core.cache import cache

T = TypeVar('T')


def build_cache_key(prefix: str, *parts: str) -> str:
    normalized = ':'.join((part or '').strip().lower() for part in parts)
    if len(normalized) > 200:
        digest = hashlib.sha256(normalized.encode()).hexdigest()
        return f'{prefix}:{digest}'
    return f'{prefix}:{normalized}'


def get_cached(prefix: str, *parts: str) -> Optional[T]:
    return cache.get(build_cache_key(prefix, *parts))


def set_cached(prefix: str, *parts: str, value: T, timeout: Optional[int] = None) -> T:
    cache.set(
        build_cache_key(prefix, *parts),
        value,
        timeout or getattr(settings, 'EXTERNAL_API_CACHE_TIMEOUT', 60 * 60 * 24),
    )
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
