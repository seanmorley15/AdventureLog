# wanderer_services.py
import requests
from datetime import datetime
from datetime import timezone as dt_timezone
from django.utils import timezone as django_timezone
from django.core.cache import cache
from django.conf import settings
import logging
import hashlib
import json

from .models import WandererIntegration

logger = logging.getLogger(__name__)

class IntegrationError(Exception):
    pass

# Use both possible cookie names
COOKIE_NAMES = ("pb_auth", "pb-auth")
LOGIN_PATH = "/api/v1/auth/login"

# Cache settings
TRAIL_CACHE_TIMEOUT = getattr(settings, 'WANDERER_TRAIL_CACHE_TIMEOUT', 60 * 15)  # 15 minutes default
TRAIL_CACHE_PREFIX = 'wanderer_trail'

def _get_cache_key(integration_id: int, trail_id: str) -> str:
    """Generate a consistent cache key for trail data."""
    return f"{TRAIL_CACHE_PREFIX}:{integration_id}:{trail_id}"

def _get_etag_cache_key(integration_id: int, trail_id: str) -> str:
    """Generate cache key for ETags."""
    return f"{TRAIL_CACHE_PREFIX}_etag:{integration_id}:{trail_id}"

def login_to_wanderer(integration: WandererIntegration, password: str):
    """
    Authenticate with Wanderer and return the auth cookie and expiry.
    """
    url = integration.server_url.rstrip("/") + LOGIN_PATH
    
    try:
        resp = requests.post(url, json={
            "username": integration.username,
            "password": password
        }, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Error connecting to Wanderer login: %s", exc)
        raise IntegrationError("Could not connect to Wanderer server.")

    # Log only summary (not full token body)
    logger.debug("Wanderer login status: %s, headers: %s", resp.status_code, resp.headers.get("Set-Cookie"))

    # Extract auth cookie and expiry
    token = None
    expiry = None
    for cookie in resp.cookies:
        if cookie.name in COOKIE_NAMES:
            token = cookie.value
            if cookie.expires:
                expiry = datetime.fromtimestamp(cookie.expires, tz=dt_timezone.utc)
            else:
                # If no expiry set, assume 24 hours from now
                expiry = django_timezone.now() + django_timezone.timedelta(hours=24)
            break

    if not token:
        logger.error("Wanderer login succeeded but no auth cookie in response.")
        raise IntegrationError("Authentication succeeded, but token cookie not found.")

    logger.info(f"Successfully authenticated with Wanderer. Token expires: {expiry}")
    return token, expiry

def get_valid_session(integration: WandererIntegration, password_for_reauth: str = None):
    """
    Get a requests session with valid authentication.
    Will reuse existing token if valid, or re-authenticate if needed.
    """
    now = django_timezone.now()
    session = requests.Session()

    if not integration:
        raise IntegrationError("No Wanderer integration found.")
    
    # Check if we have a valid token
    if integration.token and integration.token_expiry and integration.token_expiry > now:
        logger.debug("Using existing valid token")
        session.cookies.set(COOKIE_NAMES[0], integration.token)
        return session

    # Token expired or missing - need to re-authenticate
    if password_for_reauth is None:
        raise IntegrationError("Session expired; password is required to reconnect.")

    logger.info("Token expired, re-authenticating with Wanderer")
    token, expiry = login_to_wanderer(integration, password_for_reauth)
    
    # Update the integration with new token
    integration.token = token
    integration.token_expiry = expiry
    integration.save(update_fields=["token", "token_expiry"])

    # Set the cookie in the session
    session.cookies.set(COOKIE_NAMES[0], token)
    return session

def make_wanderer_request(integration: WandererIntegration, endpoint: str, method: str = "GET", password_for_reauth: str = None, **kwargs):
    """
    Helper function to make authenticated requests to Wanderer API.
    
    Args:
        integration: WandererIntegration instance
        endpoint: API endpoint (e.g., '/api/v1/list')
        method: HTTP method (GET, POST, etc.)
        password_for_reauth: Password to use if re-authentication is needed
        **kwargs: Additional arguments to pass to requests method
    
    Returns:
        requests.Response object
    """
    session = get_valid_session(integration, password_for_reauth)
    url = f"{integration.server_url.rstrip('/')}{endpoint}"
    
    try:
        response = getattr(session, method.lower())(url, timeout=10, **kwargs)
        response.raise_for_status()
        return response
    except requests.RequestException as exc:
        logger.error(f"Error making {method} request to {url}: {exc}")
        raise IntegrationError(f"Error communicating with Wanderer: {exc}")

def fetch_trail_by_id(integration: WandererIntegration, trail_id: str, password_for_reauth: str = None, use_cache: bool = True):
    """
    Fetch a specific trail by its ID from the Wanderer API with intelligent caching.
    
    Args:
        integration: WandererIntegration instance
        trail_id: ID of the trail to fetch
        password_for_reauth: Password to use if re-authentication is needed
        use_cache: Whether to use caching (default: True)
    
    Returns:
        dict: Trail data from the API
    """
    cache_key = _get_cache_key(integration.id, trail_id)
    etag_cache_key = _get_etag_cache_key(integration.id, trail_id)
    
    # Try to get from cache first
    if use_cache:
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.debug(f"Trail {trail_id} found in cache")
            return cached_data
    
    # Prepare headers for conditional requests
    headers = {}
    if use_cache:
        cached_etag = cache.get(etag_cache_key)
        if cached_etag:
            headers['If-None-Match'] = cached_etag
    
    try:
        response = make_wanderer_request(
            integration, 
            f"/api/v1/trail/{trail_id}", 
            password_for_reauth=password_for_reauth,
            headers=headers
        )
        
        # Handle 304 Not Modified
        if response.status_code == 304:
            logger.debug(f"Trail {trail_id} not modified, using cached version")
            cached_data = cache.get(cache_key)
            if cached_data:
                return cached_data
        
        trail_data = response.json()
        
        # Cache the result
        if use_cache:
            cache.set(cache_key, trail_data, TRAIL_CACHE_TIMEOUT)
            
            # Cache ETag if present
            etag = response.headers.get('ETag')
            if etag:
                cache.set(etag_cache_key, etag, TRAIL_CACHE_TIMEOUT)
                
            logger.debug(f"Trail {trail_id} cached for {TRAIL_CACHE_TIMEOUT} seconds")
        
        return trail_data
        
    except requests.RequestException as exc:
        # If we have cached data and the request fails, return cached data as fallback
        if use_cache:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.debug(f"API request failed, returning cached trail {trail_id}: {exc}")
                return cached_data
        raise

def fetch_multiple_trails_by_id(integration: WandererIntegration, trail_ids: list, password_for_reauth: str = None, use_cache: bool = True):
    """
    Fetch multiple trails efficiently with batch caching.
    
    Args:
        integration: WandererIntegration instance
        trail_ids: List of trail IDs to fetch
        password_for_reauth: Password to use if re-authentication is needed
        use_cache: Whether to use caching (default: True)
    
    Returns:
        dict: Dictionary mapping trail_id to trail data
    """
    results = {}
    uncached_ids = []
    
    if use_cache:
        # Get cache keys for all trails
        cache_keys = {trail_id: _get_cache_key(integration.id, trail_id) for trail_id in trail_ids}
        
        # Batch get from cache
        cached_trails = cache.get_many(cache_keys.values())
        key_to_id = {v: k for k, v in cache_keys.items()}
        
        # Separate cached and uncached
        for cache_key, trail_data in cached_trails.items():
            trail_id = key_to_id[cache_key]
            results[trail_id] = trail_data
            
        uncached_ids = [tid for tid in trail_ids if tid not in results]
        logger.debug(f"Found {len(results)} trails in cache, need to fetch {len(uncached_ids)}")
    else:
        uncached_ids = trail_ids
    
    # Fetch uncached trails
    for trail_id in uncached_ids:
        try:
            trail_data = fetch_trail_by_id(integration, trail_id, password_for_reauth, use_cache)
            results[trail_id] = trail_data
        except IntegrationError as e:
            logger.error(f"Failed to fetch trail {trail_id}: {e}")
            # Continue with other trails
            continue
    
    return results

def invalidate_trail_cache(integration_id: int, trail_id: str = None):
    """
    Invalidate cached trail data.
    
    Args:
        integration_id: Integration ID
        trail_id: Specific trail ID to invalidate, or None to clear all trails for this integration
    """
    if trail_id:
        # Invalidate specific trail
        cache_key = _get_cache_key(integration_id, trail_id)
        etag_cache_key = _get_etag_cache_key(integration_id, trail_id)
        cache.delete_many([cache_key, etag_cache_key])
        logger.info(f"Invalidated cache for trail {trail_id}")
    else:
        # This would require a more complex implementation to find all keys
        # For now, we'll just log it - you might want to use cache versioning instead
        logger.debug("Cache invalidation for all trails not implemented - consider using cache versioning")

def warm_trail_cache(integration: WandererIntegration, trail_ids: list, password_for_reauth: str = None):
    """
    Pre-warm the cache with trail data.
    
    Args:
        integration: WandererIntegration instance
        trail_ids: List of trail IDs to pre-load
        password_for_reauth: Password to use if re-authentication is needed
    """
    logger.info(f"Warming cache for {len(trail_ids)} trails")
    fetch_multiple_trails_by_id(integration, trail_ids, password_for_reauth, use_cache=True)

# Decorator for additional caching layers
def cached_trail_method(timeout=TRAIL_CACHE_TIMEOUT):
    """
    Decorator to add method-level caching to any function that takes integration and trail_id.
    """
    def decorator(func):
        def wrapper(integration, trail_id, *args, **kwargs):
            # Create cache key based on function name and arguments
            cache_key = f"{func.__name__}:{integration.id}:{trail_id}:{hashlib.md5(str(args).encode()).hexdigest()}"
            
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            result = func(integration, trail_id, *args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator