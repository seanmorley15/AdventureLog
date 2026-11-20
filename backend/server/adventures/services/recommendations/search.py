"""Find places worth visiting near a point, from Google Places and OpenStreetMap."""

import logging
from typing import Any, Dict, List, Optional

from django.conf import settings

from adventures.providers.recommendations import google as google_reco_provider
from adventures.providers.recommendations import osm as osm_reco_provider
from core.errors import ServiceError

from .categories import Category, get_category, resolve_category_key
from .merge import merge_results
from .parsers import parse_google_places, parse_overpass
from .scoring import score_place

logger = logging.getLogger(__name__)

# Google alone is trusted when it returns at least this many usable places.
GOOGLE_SPARSE_THRESHOLD = 8
MAX_OVERPASS_RADIUS_M = 10000
DEFAULT_LIMIT = 30
MAX_LIMIT = 50


def build_overpass_query(category: Category, lat: float, lon: float, radius: float) -> str:
    """Rounded coordinates make nearby searches share a cache entry."""
    radius = int(min(radius, MAX_OVERPASS_RADIUS_M))
    around = f'(around:{radius},{round(lat, 4)},{round(lon, 4)})'
    selectors = '\n'.join(f'  nwr["{tag}"~"^({pattern})$"]{around};' for tag, pattern in category.osm_selectors)
    return f'[out:json][timeout:8];\n(\n{selectors}\n);\nout center tags 80;'


def get_recommendations(
    lat: float,
    lon: float,
    radius: float,
    category: str,
    sources: str = 'both',
    limit: int = DEFAULT_LIMIT,
    lang: Optional[str] = None,
) -> Dict[str, Any]:
    spec = get_category(category)
    if spec is None:
        raise ServiceError(f'Unknown category: {category}', code='validation_error')

    category_key = resolve_category_key(category)
    limit = max(1, min(limit, MAX_LIMIT))
    api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
    if sources == 'google' and not api_key:
        raise ServiceError('Google Maps is not configured.', code='not_configured', status=503)

    origin = (float(lat), float(lon))
    warnings: List[str] = []
    google_results: List[Dict[str, Any]] = []
    osm_results: List[Dict[str, Any]] = []
    google_failed = False

    use_google = bool(api_key) and sources in ('google', 'both')
    if use_google:
        payload = google_reco_provider.search_nearby(
            lat, lon, radius, api_key, list(spec.google_types), max_results=20, language_code=lang or ''
        )
        if payload.error:
            google_failed = True
            warnings.append(f'Google Places: {payload.error}')
            logger.warning('Google recommendations error: %s', payload.error)
        else:
            google_results = parse_google_places(payload.data or [], origin, category_key)

    osm_only = sources == 'osm' or not use_google
    wants_osm = sources != 'google' and (osm_only or google_failed or len(google_results) < GOOGLE_SPARSE_THRESHOLD)
    osm_failed = False
    if wants_osm:
        if radius > MAX_OVERPASS_RADIUS_M:
            warnings.append('OpenStreetMap results are limited to a 10 km radius.')
        query = build_overpass_query(spec, origin[0], origin[1], radius)
        # As a top-up, never let a slow public mirror hold up results Google already gave (5 s total budget).
        osm_payload = osm_reco_provider.execute_overpass_query(
            query, timeout=15 if osm_only else 5, max_mirrors=3 if osm_only else 2
        )
        if osm_payload.error:
            osm_failed = True
            warnings.append(f'OpenStreetMap: {osm_payload.error}')
        else:
            osm_results = parse_overpass(osm_payload.data or {}, origin, category_key)

    if not google_results and not osm_results and (google_failed or osm_failed) and (
        (osm_only and osm_failed) or (google_failed and (osm_failed or not wants_osm))
    ):
        raise ServiceError(
            'No recommendation source is available right now. Please try again later.',
            code='upstream_error',
            status=503,
        )

    merged = merge_results(google_results, osm_results)
    for place in merged:
        place['quality_score'] = score_place(place, radius)
    merged.sort(key=lambda p: p['quality_score'], reverse=True)
    results = merged[:limit]

    return {
        'count': len(results),
        'category': category_key,
        'results': results,
        'sources_used': {
            'google': len(google_results),
            'osm': len(osm_results),
            'merged': len(google_results) + len(osm_results) - len(merged),
        },
        'warnings': warnings,
    }
