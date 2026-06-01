import logging
from typing import List, Dict
import requests

logger = logging.getLogger(__name__)


def get_sun_times_for_visits(latitude: float, longitude: float, visits: List[Dict]) -> List[Dict]:
    """Return sunrise/sunset times for visits given lat/lon and visit date entries.

    visits: list of dicts with keys 'start_date' and 'id'
    """
    sun_times = []
    for visit in visits:
        date = visit.get('start_date')
        if not (date and latitude and longitude):
            continue

        api_url = (
            f'https://api.sunrisesunset.io/json?'
            f'lat={latitude}&lng={longitude}&date={date}'
        )
        try:
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', {})
                if results.get('sunrise') and results.get('sunset'):
                    sun_times.append({
                        'date': date,
                        'visit_id': visit.get('id'),
                        'sunrise': results.get('sunrise'),
                        'sunset': results.get('sunset'),
                    })
        except requests.RequestException:
            logger.debug('Sun times API request failed for date %s', date)
            continue

    return sun_times
