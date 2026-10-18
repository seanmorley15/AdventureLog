from typing import Dict, List

import logging
import time

import requests

from adventures.providers.base import ProviderResult
from adventures.services.external_cache import cached_provider

logger = logging.getLogger(__name__)

# Primary and fallback Overpass endpoints
OVERPASS_URLS: List[str] = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# After every mirror fails, skip new calls so a down public instance is not hit on every search.
COOLDOWN_SECONDS = 120
_unavailable_until = 0.0


# An identical query (same area, same filters) gives the same places for hours.
@cached_provider('overpass', lambda query, *a, **k: (query,), 60 * 60 * 6)
def execute_overpass_query(query: str, timeout: int = 12) -> ProviderResult[Dict]:
    global _unavailable_until
    now = time.monotonic()
    if now < _unavailable_until:
        return ProviderResult(error="OpenStreetMap query error")

    last_error = None
    for url in OVERPASS_URLS:
        try:
            headers = {
                "User-Agent": "AdventureLog/1.0 (Overpass request)",
                "Accept": "application/json",
            }
            # Send the query as a form field named 'data' which Overpass accepts
            response = requests.post(url, data={"data": query}, timeout=timeout, headers=headers)
            if response.status_code == 429 or response.status_code >= 500:
                last_error = f"{response.status_code} from {url}"
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
            _unavailable_until = 0.0
            return ProviderResult(data=data)

        except requests.exceptions.RequestException as e:
            last_error = str(e)
            continue

    _unavailable_until = time.monotonic() + COOLDOWN_SECONDS
    if last_error:
        logger.warning("All Overpass mirrors were unavailable: %s", last_error)
    return ProviderResult(error="OpenStreetMap query error")
