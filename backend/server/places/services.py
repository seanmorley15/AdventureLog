import hashlib
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from . import overpass_client
from .models import OverpassCacheEntry

DEFAULT_TTL_DAYS = getattr(settings, 'PLACES_OVERPASS_CACHE_TTL_DAYS', 14)


def normalize_query_key(lat, lon, radius, category):
    """Deterministic cache key: same search in any param order/formatting → same key.

    Coordinates are rounded to 4 decimal places (~11m precision) so nearly
    identical stops share a cache entry without merging genuinely distinct
    searches.
    """
    normalized = {
        'category': category,
        'lat': round(float(lat), 4),
        'lon': round(float(lon), 4),
        'radius': int(radius),
    }
    canonical = '&'.join(f'{k}={normalized[k]}' for k in sorted(normalized))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def get_nearby_places(lat, lon, radius, category, ttl_days=None):
    """Cache-first Overpass lookup. Returns {"error": str|None, "results": list, "cached": bool}."""
    ttl_days = DEFAULT_TTL_DAYS if ttl_days is None else ttl_days
    query_key = normalize_query_key(lat, lon, radius, category)

    entry = OverpassCacheEntry.objects.filter(
        query_key=query_key, expires_at__gt=timezone.now()
    ).first()
    if entry is not None:
        payload = entry.payload
        return {'error': payload.get('error'), 'results': payload.get('results', []), 'cached': True}

    result = overpass_client.fetch_nearby(lat, lon, radius, category)

    # Don't cache transient errors (empty results due to Overpass being down) —
    # only cache successful responses so a retry after an outage isn't stuck
    # serving an empty cached error for the whole TTL window.
    if result.get('error') is None:
        OverpassCacheEntry.objects.update_or_create(
            query_key=query_key,
            defaults={
                'payload': {'error': None, 'results': result['results']},
                'expires_at': timezone.now() + timedelta(days=ttl_days),
            },
        )

    result['cached'] = False
    return result
