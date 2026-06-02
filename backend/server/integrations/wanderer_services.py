import hashlib
import logging
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.cache import cache

from .models import WandererIntegration

logger = logging.getLogger(__name__)


class IntegrationError(Exception):
    pass


TRAIL_CACHE_TIMEOUT = getattr(settings, 'WANDERER_TRAIL_CACHE_TIMEOUT', 60 * 15)
TRAIL_CACHE_PREFIX = 'wanderer_trail_v3'
# PocketBase / wanderer.to uses singular /trail; newer builds may also expose plural /trails
TRAILS_LIST_PATHS = ('/api/v1/trail', '/api/v1/trails')
TRAILS_LIST_PATH = TRAILS_LIST_PATHS[0]
TRAIL_DETAIL_PATHS = ('/api/v1/trail/{trail_id}', '/api/v1/trails/{trail_id}')
TRAIL_EXPAND_AUTHOR = {'expand': 'author'}
GPX_GEOJSON_CACHE_PREFIX = 'wanderer_trail_geojson'
GPX_FILES_PATH = '/api/v1/files/trails/{trail_id}/{gpx_filename}'


def extract_wanderer_author_from_trail(trail_data: dict | None) -> tuple[str | None, str | None]:
    """
    Read username and domain from expand.author on a Wanderer trail payload.
    """
    if not trail_data:
        return None, None
    expand = trail_data.get('expand')
    if not isinstance(expand, dict):
        return None, None
    author = expand.get('author')
    if not isinstance(author, dict):
        return None, None

    username = (
        author.get('preferred_username')
        or author.get('username')
    )
    if username:
        username = str(username).strip() or None

    domain = author.get('domain')
    if domain:
        domain = str(domain).strip().lstrip('@') or None

    return username, domain


def build_wanderer_trail_view_url(
    viewer_server_url: str,
    trail_id: str,
    author_username: str,
    author_domain: str,
) -> str:
    base_url = normalize_server_url(viewer_server_url)
    return (
        f"{base_url}/trail/view/@{author_username}@{author_domain}/{trail_id}"
    )


def _get_cache_key(integration_id, trail_id: str) -> str:
    return f"{TRAIL_CACHE_PREFIX}:{integration_id}:{trail_id}"


def _get_etag_cache_key(integration_id, trail_id: str) -> str:
    return f"{TRAIL_CACHE_PREFIX}_etag:{integration_id}:{trail_id}"


def _gpx_geojson_cache_key(integration_id, trail_id: str, gpx_filename: str) -> str:
    return f"{GPX_GEOJSON_CACHE_PREFIX}:{integration_id}:{trail_id}:{gpx_filename}"


def normalize_server_url(server_url: str) -> str:
    url = (server_url or '').strip().rstrip('/')
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        raise IntegrationError('Server URL must be a valid http or https URL.')
    return url


def _auth_headers(api_key: str) -> dict:
    key = (api_key or '').strip()
    if not key:
        raise IntegrationError('API key is required.')
    return {'Authorization': f'Bearer {key}'}


def validate_wanderer_connection(server_url: str, api_key: str) -> str:
    """
    Verify server URL and API key against Wanderer. Returns normalized server_url.
    """
    normalized_url = normalize_server_url(server_url)
    headers = _auth_headers(api_key)
    last_status = None

    for path in TRAILS_LIST_PATHS:
        url = f"{normalized_url}{path}"
        try:
            response = requests.get(
                url,
                headers=headers,
                params={'perPage': 1},
                timeout=10,
            )
        except requests.RequestException as exc:
            logger.error("Error connecting to Wanderer at %s: %s", url, exc)
            raise IntegrationError('Could not connect to Wanderer server.') from exc

        if response.status_code in (401, 403):
            raise IntegrationError('Invalid Wanderer API key.')
        if response.status_code < 400:
            return normalized_url
        last_status = response.status_code
        if response.status_code != 404:
            break

    if last_status == 404:
        raise IntegrationError(
            'Wanderer API endpoint not found. Check the server URL points to your Wanderer instance.'
        )
    raise IntegrationError(
        f'Wanderer server rejected the connection request (HTTP {last_status}).'
    )


def make_wanderer_request(
    integration: WandererIntegration,
    endpoint: str,
    method: str = 'GET',
    **kwargs,
):
    if not integration:
        raise IntegrationError('No Wanderer integration found.')

    url = f"{integration.server_url.rstrip('/')}{endpoint}"
    headers = {**_auth_headers(integration.api_key), **kwargs.pop('headers', {})}

    try:
        response = requests.request(
            method.upper(),
            url,
            headers=headers,
            timeout=10,
            **kwargs,
        )
        response.raise_for_status()
        return response
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code in (401, 403):
            raise IntegrationError('Invalid or revoked Wanderer API key.') from exc
        logger.error("Error making %s request to %s: %s", method, url, exc)
        raise IntegrationError(f'Error communicating with Wanderer: {exc}') from exc
    except requests.RequestException as exc:
        logger.error("Error making %s request to %s: %s", method, url, exc)
        raise IntegrationError(f'Error communicating with Wanderer: {exc}') from exc


def fetch_trail_by_id(
    integration: WandererIntegration,
    trail_id: str,
    use_cache: bool = True,
):
    cache_key = _get_cache_key(integration.id, trail_id)
    etag_cache_key = _get_etag_cache_key(integration.id, trail_id)

    if use_cache:
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.debug("Trail %s found in cache", trail_id)
            return cached_data

    headers = {}
    if use_cache:
        cached_etag = cache.get(etag_cache_key)
        if cached_etag:
            headers['If-None-Match'] = cached_etag

    try:
        response = None
        last_error = None
        for detail_template in TRAIL_DETAIL_PATHS:
            detail_path = detail_template.format(trail_id=trail_id)
            try:
                response = make_wanderer_request(
                    integration,
                    detail_path,
                    headers=headers,
                    params=TRAIL_EXPAND_AUTHOR,
                )
                break
            except IntegrationError as exc:
                last_error = exc
                if '404' in str(exc):
                    continue
                raise

        if response is None:
            raise last_error or IntegrationError('Trail not found on Wanderer server.')

        if response.status_code == 304:
            logger.debug("Trail %s not modified, using cached version", trail_id)
            cached_data = cache.get(cache_key)
            if cached_data:
                return cached_data

        trail_data = response.json()

        if use_cache:
            cache.set(cache_key, trail_data, TRAIL_CACHE_TIMEOUT)
            etag = response.headers.get('ETag')
            if etag:
                cache.set(etag_cache_key, etag, TRAIL_CACHE_TIMEOUT)
            logger.debug("Trail %s cached for %s seconds", trail_id, TRAIL_CACHE_TIMEOUT)

        return trail_data

    except IntegrationError:
        raise
    except requests.RequestException as exc:
        if use_cache:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.debug(
                    "API request failed, returning cached trail %s: %s",
                    trail_id,
                    exc,
                )
                return cached_data
        raise


def fetch_trail_gpx(
    integration: WandererIntegration,
    trail_id: str,
    gpx_filename: str,
) -> bytes:
    if not gpx_filename:
        raise IntegrationError('GPX filename is required.')

    endpoint = GPX_FILES_PATH.format(trail_id=trail_id, gpx_filename=gpx_filename)
    response = make_wanderer_request(integration, endpoint)
    return response.content


def fetch_trail_geojson(
    integration: WandererIntegration,
    trail_id: str,
    trail_data: dict | None = None,
    use_cache: bool = True,
):
    """
    Download Wanderer GPX for a trail, convert to GeoJSON, and cache the result.
    Returns None if the trail has no GPX or conversion fails.
    """
    from adventures.utils.geojson import gpx_bytes_to_geojson

    if trail_data is None:
        try:
            trail_data = fetch_trail_by_id(integration, trail_id, use_cache=use_cache)
        except IntegrationError as exc:
            logger.warning("Could not fetch Wanderer trail %s for GeoJSON: %s", trail_id, exc)
            return None

    gpx_filename = (trail_data or {}).get('gpx')
    if not gpx_filename or not str(gpx_filename).strip():
        return None

    gpx_filename = str(gpx_filename).strip()
    cache_key = _gpx_geojson_cache_key(integration.id, trail_id, gpx_filename)

    if use_cache:
        cached_geojson = cache.get(cache_key)
        if cached_geojson is not None:
            logger.debug("GeoJSON for trail %s found in cache", trail_id)
            return cached_geojson

    try:
        gpx_content = fetch_trail_gpx(integration, trail_id, gpx_filename)
        geojson_data = gpx_bytes_to_geojson(gpx_content)
    except IntegrationError as exc:
        logger.warning("Could not download GPX for trail %s: %s", trail_id, exc)
        return None
    except Exception as exc:
        logger.warning("Could not convert GPX for trail %s: %s", trail_id, exc)
        return None

    if not geojson_data or isinstance(geojson_data, dict) and geojson_data.get('error'):
        logger.warning(
            "GPX conversion failed for trail %s: %s",
            trail_id,
            geojson_data.get('message') if isinstance(geojson_data, dict) else 'unknown error',
        )
        return None

    if use_cache:
        cache.set(cache_key, geojson_data, TRAIL_CACHE_TIMEOUT)
        logger.debug("GeoJSON for trail %s cached for %s seconds", trail_id, TRAIL_CACHE_TIMEOUT)

    return geojson_data


def fetch_multiple_trails_by_id(
    integration: WandererIntegration,
    trail_ids: list,
    use_cache: bool = True,
):
    results = {}
    uncached_ids = []

    if use_cache:
        cache_keys = {
            trail_id: _get_cache_key(integration.id, trail_id) for trail_id in trail_ids
        }
        cached_trails = cache.get_many(cache_keys.values())
        key_to_id = {v: k for k, v in cache_keys.items()}

        for cache_key, trail_data in cached_trails.items():
            trail_id = key_to_id[cache_key]
            results[trail_id] = trail_data

        uncached_ids = [tid for tid in trail_ids if tid not in results]
        logger.debug(
            "Found %s trails in cache, need to fetch %s",
            len(results),
            len(uncached_ids),
        )
    else:
        uncached_ids = trail_ids

    for trail_id in uncached_ids:
        try:
            trail_data = fetch_trail_by_id(integration, trail_id, use_cache)
            results[trail_id] = trail_data
        except IntegrationError as e:
            logger.error("Failed to fetch trail %s: %s", trail_id, e)

    return results


def invalidate_trail_cache(integration_id, trail_id: str = None):
    if trail_id:
        cache_key = _get_cache_key(integration_id, trail_id)
        etag_cache_key = _get_etag_cache_key(integration_id, trail_id)
        cached_trail = cache.get(cache_key)
        keys_to_delete = [cache_key, etag_cache_key]
        if isinstance(cached_trail, dict):
            gpx_filename = cached_trail.get('gpx')
            if gpx_filename:
                keys_to_delete.append(
                    _gpx_geojson_cache_key(integration_id, trail_id, str(gpx_filename).strip())
                )
        cache.delete_many(keys_to_delete)
        logger.info("Invalidated cache for trail %s", trail_id)
    else:
        logger.debug(
            "Cache invalidation for all trails not implemented - consider using cache versioning"
        )


def warm_trail_cache(integration: WandererIntegration, trail_ids: list):
    logger.info("Warming cache for %s trails", len(trail_ids))
    fetch_multiple_trails_by_id(integration, trail_ids, use_cache=True)


def cached_trail_method(timeout=TRAIL_CACHE_TIMEOUT):
    def decorator(func):
        def wrapper(integration, trail_id, *args, **kwargs):
            cache_key = (
                f"{func.__name__}:{integration.id}:{trail_id}:"
                f"{hashlib.md5(str(args).encode()).hexdigest()}"
            )
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            result = func(integration, trail_id, *args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result

        return wrapper

    return decorator
