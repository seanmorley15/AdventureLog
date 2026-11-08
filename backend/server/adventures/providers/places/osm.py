from typing import Dict, List, Optional

import requests

from django.conf import settings

from core.results import ProviderResult
from core.cache import cached_provider

SEARCH_URL = "https://nominatim.openstreetmap.org/search"

# OpenStreetMap's usage policies ask clients to cache. One setting covers every OSM lookup.
OSM_CACHE_TIMEOUT = getattr(settings, 'OSM_CACHE_TIMEOUT', 60 * 60 * 24)


def _headers(user_agent: str, language: Optional[str]) -> Dict[str, str]:
    headers = {"User-Agent": user_agent}
    if language:
        headers["Accept-Language"] = language
    return headers


# Names come back in the requested language, so the language is part of the key.
@cached_provider(
    'osm_search',
    lambda query, limit=20, user_agent=None, language=None, **k: (query, limit, language or ''),
    OSM_CACHE_TIMEOUT,
)
def search_places(
    query: str,
    limit: int = 20,
    user_agent: str = "AdventureLog Server",
    language: Optional[str] = None,
) -> ProviderResult[List[Dict]]:
    headers = _headers(user_agent, language)
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": limit,
    }

    try:
        response = requests.get(SEARCH_URL, headers=headers, params=params, timeout=(2, 5))
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return ProviderResult(error="Request timed out while contacting OpenStreetMap")
    except requests.exceptions.RequestException:
        return ProviderResult(error="OpenStreetMap service error")

    return ProviderResult(data=response.json() or [])
