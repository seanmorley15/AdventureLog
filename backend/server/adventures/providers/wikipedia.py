"""Wikipedia over HTTP.

Two APIs, kept separate because they behave differently:

* ``fetch_summary`` - the REST page-summary endpoint. Quiet: any failure is just "no summary".
* ``WikipediaClient`` - the MediaWiki action API (search, page extracts, page images). Raises on
  HTTP errors; callers decide what to skip.
"""

import logging
from difflib import SequenceMatcher
from typing import Dict, List, Optional
from urllib.parse import quote

import requests
from django.conf import settings

from core.results import ProviderResult
from core.cache import get_or_fetch_cached

logger = logging.getLogger(__name__)

WIKIPEDIA_SUMMARY_CACHE_PREFIX = 'wikipedia_summary_v1'
WIKIPEDIA_SUMMARY_CACHE_TIMEOUT = getattr(settings, 'WIKIPEDIA_SUMMARY_CACHE_TIMEOUT', 60 * 60 * 24 * 7)


def fetch_summary(query: str, language: str = "en") -> ProviderResult[Optional[str]]:
    normalized_query = (query or "").strip()
    if not normalized_query:
        return ProviderResult(error="Missing query")

    normalized_language = (language or "en").strip().lower() or "en"

    def fetch() -> Optional[str]:
        return _fetch_summary_uncached(normalized_query, normalized_language)

    cached = get_or_fetch_cached(
        WIKIPEDIA_SUMMARY_CACHE_PREFIX,
        normalized_language,
        normalized_query,
        fetch_fn=fetch,
        timeout=WIKIPEDIA_SUMMARY_CACHE_TIMEOUT,
    )
    if cached:
        return ProviderResult(data=cached)
    return ProviderResult(data=None)


def _fetch_summary_uncached(query: str, language: str) -> Optional[str]:
    candidates = [query]
    if "," in query:
        head = query.split(",")[0].strip()
        if head and head not in candidates:
            candidates.append(head)

    for candidate in candidates:
        try:
            encoded_query = quote(candidate, safe="")
            url = f"https://{language.split('-', 1)[0]}.wikipedia.org/api/rest_v1/page/summary/{encoded_query}"
            response = requests.get(
                url,
                headers={"User-Agent": "AdventureLog Server"},
                timeout=(2, 5),
            )
            if response.status_code != 200:
                continue

            data = response.json() or {}
            if data.get("type") == "disambiguation":
                continue

            extract = (data.get("extract") or "").strip()
            if len(extract) >= 120:
                return extract
        except requests.exceptions.RequestException:
            continue

    return None


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
