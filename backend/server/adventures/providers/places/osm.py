from typing import Dict, List, Optional

import requests

from adventures.providers.base import ProviderResult

SEARCH_URL = "https://nominatim.openstreetmap.org/search"


def _headers(user_agent: str, language: Optional[str]) -> Dict[str, str]:
    headers = {"User-Agent": user_agent}
    if language:
        headers["Accept-Language"] = language
    return headers


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
