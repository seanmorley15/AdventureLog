import socket
from typing import Dict

import requests

from adventures.providers.base import ProviderResult

REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"


def _is_host_resolvable(hostname: str) -> bool:
    try:
        socket.gethostbyname(hostname)
        return True
    except socket.error:
        return False


def reverse_geocode(lat: float, lon: float, user_agent: str = "AdventureLog Server") -> ProviderResult[Dict]:
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
    headers = {"User-Agent": user_agent}

    try:
        response = requests.get(REVERSE_URL, headers=headers, params=params, timeout=(1, 5))
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return ProviderResult(error="Request timed out while contacting OpenStreetMap")
    except requests.exceptions.RequestException:
        return ProviderResult(error="OpenStreetMap service error")

    return ProviderResult(data=response.json() or {})
