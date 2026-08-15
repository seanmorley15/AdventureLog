import logging
from typing import TypedDict

import requests

from adventures.providers.base import ProviderResult

logger = logging.getLogger(__name__)

API_BASE_URL = 'https://api.sunrisesunset.io/json'


class SunriseSunsetData(TypedDict):
    date: str
    sunrise: str
    sunset: str


def fetch_sunrise_sunset(latitude: float, longitude: float, date: str) -> ProviderResult[SunriseSunsetData]:
    """Fetch sunrise and sunset for a coordinate and calendar date (YYYY-MM-DD)."""
    if latitude is None or longitude is None:
        return ProviderResult(error='Missing coordinates')
    if not date:
        return ProviderResult(error='Missing date')

    api_url = f'{API_BASE_URL}?lat={latitude}&lng={longitude}&date={date}'
    try:
        response = requests.get(api_url, timeout=10)
    except requests.RequestException as exc:
        logger.warning('Sunrise/sunset API request failed for %s: %s', date, exc)
        return ProviderResult(error='Sunrise/sunset API request failed')

    if response.status_code != 200:
        logger.warning('Sunrise/sunset API returned status %s for %s', response.status_code, date)
        return ProviderResult(error='Sunrise/sunset API returned an error')

    data = response.json() or {}
    results = data.get('results', {})
    sunrise = results.get('sunrise')
    sunset = results.get('sunset')
    if not sunrise or not sunset:
        return ProviderResult(error='Sunrise/sunset not available for this date')

    return ProviderResult(data={
        'date': date,
        'sunrise': sunrise,
        'sunset': sunset,
    })
