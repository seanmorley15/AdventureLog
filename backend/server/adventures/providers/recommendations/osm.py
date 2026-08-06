from typing import Dict, List

import logging
import requests

from adventures.providers.base import ProviderResult

logger = logging.getLogger(__name__)

# Primary and fallback Overpass endpoints
OVERPASS_URLS: List[str] = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def execute_overpass_query(query: str, timeout: int = 30) -> ProviderResult[Dict]:
    last_exception = None
    for url in OVERPASS_URLS:
        try:
            headers = {
                "User-Agent": "AdventureLog/1.0 (Overpass request)",
                "Accept": "application/json",
            }
            # Send the query as a form field named 'data' which Overpass accepts
            response = requests.post(url, data={"data": query}, timeout=timeout, headers=headers)
            # If the server returns a 5xx or 4xx, log body for debugging
            if response.status_code != 200:
                logger.warning("Overpass server %s returned status %s: %s", url, response.status_code, response.text[:1024])
                response.raise_for_status()
            try:
                data = response.json() or {}
            except ValueError:
                logger.exception("Invalid JSON from Overpass server %s", url)
                return ProviderResult(error="Invalid OpenStreetMap response")
            return ProviderResult(data=data)

        except requests.exceptions.Timeout as e:
            logger.warning("Overpass timeout from %s: %s", url, str(e))
            last_exception = e
            continue
        except requests.exceptions.RequestException as e:
            logger.warning("Overpass request failed for %s: %s", url, str(e))
            last_exception = e
            continue

    # If we get here, all endpoints failed
    if last_exception:
        logger.exception("All Overpass endpoints failed: %s", str(last_exception))
        return ProviderResult(error="OpenStreetMap query error")

    return ProviderResult(error="OpenStreetMap query error")
