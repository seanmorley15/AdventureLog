from typing import Dict, List

import logging
import time

import requests

from django.conf import settings

from core.results import ProviderResult
from core.cache import cached_provider

logger = logging.getLogger(__name__)

# Primary and fallback Overpass endpoints
OVERPASS_URLS: List[str] = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# A mirror that just failed or timed out is skipped for this long, so one dead public
# instance does not add its full timeout to every search.
MIRROR_COOLDOWN_SECONDS = 120
CONNECT_TIMEOUT = 3

# OpenStreetMap's usage policies ask clients to cache. One setting covers every OSM lookup.
OSM_CACHE_TIMEOUT = getattr(settings, 'OSM_CACHE_TIMEOUT', 60 * 60 * 24)
_mirror_unavailable_until: Dict[str, float] = {}


def _mark_down(url: str) -> None:
    _mirror_unavailable_until[url] = time.monotonic() + MIRROR_COOLDOWN_SECONDS


# An identical query (same area, same filters) gives the same places, empty answers included.
@cached_provider('overpass', lambda query, *a, **k: (query,), OSM_CACHE_TIMEOUT)
def execute_overpass_query(query: str, timeout: int = 12, max_mirrors: int = len(OVERPASS_URLS)) -> ProviderResult[Dict]:
    """Try up to ``max_mirrors`` healthy mirrors in order. ``timeout`` is the total time budget, not per mirror."""
    deadline = time.monotonic() + timeout
    now = time.monotonic()
    mirrors = [u for u in OVERPASS_URLS if _mirror_unavailable_until.get(u, 0.0) <= now][:max_mirrors]
    if not mirrors:
        return ProviderResult(error="OpenStreetMap query error")

    last_error = None
    for url in mirrors:
        remaining = deadline - time.monotonic()
        if remaining <= 0.5:
            break
        try:
            headers = {
                "User-Agent": "AdventureLog/1.0 (Overpass request)",
                "Accept": "application/json",
            }
            # Send the query as a form field named 'data' which Overpass accepts
            response = requests.post(
                url, data={"data": query}, timeout=(min(CONNECT_TIMEOUT, remaining), remaining), headers=headers
            )
            if response.status_code == 429 or response.status_code >= 500:
                last_error = f"{response.status_code} from {url}"
                _mark_down(url)
                continue
            if response.status_code != 200:
                last_error = f"{response.status_code} from {url}"
                logger.warning(
                    "Overpass server %s returned status %s: %s",
                    url,
                    response.status_code,
                    response.text[:1024],
                )
                continue
            try:
                data = response.json() or {}
            except ValueError:
                logger.warning("Invalid JSON from Overpass server %s", url)
                return ProviderResult(error="Invalid OpenStreetMap response")
            _mirror_unavailable_until.pop(url, None)
            return ProviderResult(data=data)

        except requests.exceptions.RequestException as e:
            last_error = str(e)
            _mark_down(url)
            continue

    if last_error:
        logger.warning("All Overpass mirrors were unavailable: %s", last_error)
    return ProviderResult(error="OpenStreetMap query error")
