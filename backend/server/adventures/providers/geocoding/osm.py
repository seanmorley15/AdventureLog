from typing import Dict

import requests

from core.results import ProviderResult
from core.cache import cached_provider, coordinate_key
from core.net import is_resolvable

GEOCODE_CACHE_TIMEOUT = 60 * 60 * 24 * 7  # Nominatim asks clients to cache results

REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"


@cached_provider(
    'osm_reverse',
    lambda lat, lon, *a, **k: (coordinate_key(lat, 5), coordinate_key(lon, 5)),
    GEOCODE_CACHE_TIMEOUT,
)
def reverse_geocode(lat: float, lon: float, user_agent: str = "AdventureLog Server") -> ProviderResult[Dict]:
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
    headers = {"User-Agent": user_agent}

    try:
        response = requests.get(REVERSE_URL, headers=headers, params=params, timeout=(1, 5))
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return ProviderResult(error="Request timed out while contacting OpenStreetMap")
    except requests.exceptions.RequestException:
        return ProviderResult(error="OpenStreetMap service error")

    return ProviderResult(data=response.json() or {})
