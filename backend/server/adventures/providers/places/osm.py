from typing import Dict, List

import requests

from adventures.providers.base import ProviderResult
from adventures.services.external_cache import cached_provider, coordinate_key

SEARCH_URL = "https://nominatim.openstreetmap.org/search"


@cached_provider('osm_search', lambda query, limit=20, *a, **k: (query, limit), 60 * 60 * 24)
def search_places(query: str, limit: int = 20, user_agent: str = "AdventureLog Server") -> ProviderResult[List[Dict]]:
    headers = {"User-Agent": user_agent}
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
