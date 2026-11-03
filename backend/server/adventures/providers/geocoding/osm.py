from typing import Dict, Optional

import requests

from core.results import ProviderResult
from core.cache import cached_provider, coordinate_key
from core.net import is_resolvable

GEOCODE_CACHE_TIMEOUT = 60 * 60 * 24 * 7  # Nominatim asks clients to cache results

REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"


def _headers(user_agent: str, language: Optional[str]) -> Dict[str, str]:
    headers = {"User-Agent": user_agent}
    if language:
        headers["Accept-Language"] = language
    return headers


@cached_provider(
    'osm_reverse',
    # Names come back in the requested language, so the language is part of the key.
    lambda lat, lon, user_agent=None, language=None, **k: (
        coordinate_key(lat, 5),
        coordinate_key(lon, 5),
        language or '',
    ),
    GEOCODE_CACHE_TIMEOUT,
)
def reverse_geocode(
    lat: float,
    lon: float,
    user_agent: str = "AdventureLog Server",
    language: Optional[str] = None,
) -> ProviderResult[Dict]:
    if not is_resolvable("nominatim.openstreetmap.org"):
        return ProviderResult(error="Unable to resolve OpenStreetMap service")

    params = {
        "format": "jsonv2",
        "addressdetails": 1,
        "namedetails": 1,
        "extratags": 1,
        "zoom": 18,
        "lat": lat,
        "lon": lon,
    }
    headers = _headers(user_agent, language)

    try:
        response = requests.get(REVERSE_URL, headers=headers, params=params, timeout=(1, 5))
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return ProviderResult(error="Request timed out while contacting OpenStreetMap")
    except requests.exceptions.RequestException:
        return ProviderResult(error="OpenStreetMap service error")

    return ProviderResult(data=response.json() or {})
