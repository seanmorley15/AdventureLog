import logging
import urllib.parse
from difflib import SequenceMatcher
from typing import List, Dict, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class WikipediaClient:
    BASE_HEADERS = {
        'User-Agent': f'AdventureLog/{getattr(settings, "ADVENTURELOG_RELEASE_VERSION", "unknown")}'
    }
    DEFAULT_LANGUAGE = 'en'
    LANGUAGE_PATTERN = r'^[a-z0-9-]{2,12}$'
    ACCEPTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

    def __init__(self):
        pass

    def build_api_url(self, lang: str) -> str:
        subdomain = lang.split('-', 1)[0]
        return f'https://{subdomain}.wikipedia.org/w/api.php'

    def get_headers(self, lang: str) -> Dict[str, str]:
        headers = dict(self.BASE_HEADERS)
        headers['Accept-Language'] = lang
        headers['Accept'] = 'application/json'
        return headers

    def get_candidate_pages(self, term: str, lang: str, max_candidates: int = 10) -> List[Dict[str, Optional[int]]]:
        if not term:
            return []

        url = self.build_api_url(lang)
        params = {
            'origin': '*',
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'srsearch': term,
            'srlimit': max_candidates,
            'srwhat': 'text',
            'utf8': 1,
        }

        resp = requests.get(url, headers=self.get_headers(lang), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        search_results = data.get('query', {}).get('search', [])
        if not search_results:
            return [{'title': term, 'pageid': None}]

        normalized = term.lower()
        ranked_results = []
        for result in search_results:
            title = (result.get('title') or '').strip()
            if not title:
                continue
            title_lower = title.lower()
            similarity = SequenceMatcher(None, normalized, title_lower).ratio()
            exact_match = int(title_lower == normalized)
            starts_with = int(title_lower.startswith(normalized))
            is_disambig = int('disambiguation' in title_lower or '(disambig' in title_lower)
            is_list = int(any(p in title_lower for p in ['list of', 'index of', 'timeline of']))
            score = result.get('score') or 0
            ranked_results.append({
                'title': title,
                'pageid': result.get('pageid'),
                'exact': exact_match,
                'starts_with': starts_with,
                'similarity': similarity,
                'score': score,
                'is_disambig': is_disambig,
                'is_list': is_list,
            })

        ranked_results.sort(
            key=lambda e: (
                e['exact'],
                e['starts_with'],
                -e['is_disambig'],
                -e['is_list'],
                e['similarity'],
                e['score'],
            ),
            reverse=True,
        )

        candidates = []
        seen = set()
        for entry in ranked_results:
            key = entry['title'].lower()
            if key in seen:
                continue
            seen.add(key)
            candidates.append({'title': entry['title'], 'pageid': entry['pageid']})
            if len(candidates) >= max_candidates:
                break

        if term.lower() not in seen:
            candidates.append({'title': term, 'pageid': None})

        return candidates

    def fetch_page(self, lang: str, candidate: Dict[str, Optional[int]], props: str, extra_params: Optional[Dict] = None) -> Optional[Dict]:
        if not candidate or not candidate.get('title'):
            return None
        params = {
            'origin': '*',
            'action': 'query',
            'format': 'json',
            'prop': props,
        }
        page_id = candidate.get('pageid')
        if page_id:
            params['pageids'] = page_id
        else:
            params['titles'] = candidate['title']
        if extra_params:
            params.update(extra_params)

        resp = requests.get(self.build_api_url(lang), headers=self.get_headers(lang), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        pages = data.get('query', {}).get('pages', {})
        if not pages:
            return None
        if page_id is not None:
            page_data = pages.get(str(page_id))
            if page_data:
                page_data.setdefault('title', candidate['title'])
                return page_data
        page_data = next(iter(pages.values()))
        if page_data:
            page_data.setdefault('title', candidate['title'])
        return page_data


def is_valid_image_url(url: Optional[str]) -> bool:
    if not url:
        return False
    url_lower = url.lower()
    if '.svg' in url_lower:
        return False
    return any(url_lower.endswith(fmt) or fmt in url_lower for fmt in WikipediaClient.ACCEPTED_IMAGE_FORMATS)
