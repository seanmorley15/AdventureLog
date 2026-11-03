import socket
from typing import Dict, Optional

import requests

from adventures.providers.base import ProviderResult

REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"


def _headers(user_agent: str, language: Optional[str]) -> Dict[str, str]:
    headers = {"User-Agent": user_agent}
    if language:
        headers["Accept-Language"] = language
    return headers


def _is_host_resolvable(hostname: str) -> bool:
    try:
        socket.gethostbyname(hostname)
        return True
    except socket.error:
        return False


def reverse_geocode(
    lat: float,
    lon: float,
    user_agent: str = "AdventureLog Server",
    language: Optional[str] = None,
) -> ProviderResult[Dict]:
    if not _is_host_resolvable("nominatim.openstreetmap.org"):
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
