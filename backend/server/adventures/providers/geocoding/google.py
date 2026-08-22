from typing import Dict

import requests

from adventures.providers.base import ProviderResult

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def reverse_geocode(lat: float, lon: float, api_key: str) -> ProviderResult[Dict]:
    if not api_key:
        return ProviderResult(error="Google Maps API key not configured")

    params = {"latlng": f"{lat},{lon}", "key": api_key}

    try:
        response = requests.get(GEOCODE_URL, params=params, timeout=(2, 5))
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return ProviderResult(error="Request timed out while contacting Google Maps")
    except requests.exceptions.RequestException:
        return ProviderResult(error="Google Maps service error")

    data = response.json() or {}
    status = data.get("status")
    if status and status != "OK":
        return ProviderResult(error=f"Google Maps geocoding error: {status}")

    return ProviderResult(data=data)
