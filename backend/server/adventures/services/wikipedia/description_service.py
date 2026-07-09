import logging
import re
from typing import Dict, List, Optional

from difflib import SequenceMatcher
from django.conf import settings

from adventures.services.external_cache import get_or_fetch_cached
from adventures.services.wikipedia.search import WikipediaClient, is_valid_image_url

logger = logging.getLogger(__name__)

WIKIPEDIA_DESC_CACHE_PREFIX = 'wikipedia_desc_v1'
WIKIPEDIA_DESC_CACHE_TIMEOUT = getattr(settings, 'WIKIPEDIA_DESC_CACHE_TIMEOUT', 60 * 60 * 24 * 7)


class WikipediaDescriptionService:
    LANGUAGE_PATTERN = re.compile(r"^[a-z0-9-]{2,12}$", re.IGNORECASE)
    MAX_CANDIDATES = 10
    MIN_DESCRIPTION_LENGTH = 50

    def __init__(self, client: Optional[WikipediaClient] = None, max_candidates: int = None):
        self.client = client or WikipediaClient()
        if max_candidates:
            self.MAX_CANDIDATES = max_candidates

    def get_language(self, candidate: Optional[str]) -> str:
        if not candidate:
            candidate = self.client.DEFAULT_LANGUAGE
        normalized = candidate.replace('_', '-').lower()
        if self.LANGUAGE_PATTERN.match(normalized):
            return normalized
        return 'en'

    def is_disambiguation_page(self, page_data: Dict) -> bool:
        categories = page_data.get('categories', [])
        for cat in categories:
            cat_title = cat.get('title', '').lower()
            if 'disambiguation' in cat_title or 'disambig' in cat_title:
                return True

        title = page_data.get('title', '').lower()
        if '(disambiguation)' in title:
            return True
        return False

    def is_list_or_index_page(self, page_data: Dict) -> bool:
        title = page_data.get('title', '').lower()
        list_patterns = ['list of', 'index of', 'timeline of', 'glossary of', 'outline of']
        return any(p in title for p in list_patterns)

    def get_description(self, term: str, lang: str) -> Optional[Dict]:
        if not term:
            return None

        normalized_term = term.strip()
        normalized_lang = self.get_language(lang)

        def fetch() -> Optional[Dict]:
            return self._fetch_description(normalized_term, normalized_lang)

        return get_or_fetch_cached(
            WIKIPEDIA_DESC_CACHE_PREFIX,
            normalized_lang,
            normalized_term,
            fetch_fn=fetch,
            timeout=WIKIPEDIA_DESC_CACHE_TIMEOUT,
        )

    def _fetch_description(self, term: str, lang: str) -> Optional[Dict]:
        candidates = self.client.get_candidate_pages(term, lang, max_candidates=self.MAX_CANDIDATES)
        for candidate in candidates:
            try:
                page_data = self.client.fetch_page(lang=lang, candidate=candidate, props='extracts|categories', extra_params={'exintro': 1, 'explaintext': 1})
            except Exception:
                logger.exception('Error fetching page %s', candidate)
                continue
            if not page_data or page_data.get('missing'):
                continue
            if self.is_disambiguation_page(page_data):
                continue
            extract = (page_data.get('extract') or '').strip()
            if len(extract) < self.MIN_DESCRIPTION_LENGTH:
                continue
            if self.is_list_or_index_page(page_data):
                continue
            page_data['lang'] = lang
            return page_data
        return None

    def get_images(self, term: str, lang: str, limit: int = 8) -> List[Dict]:
        if not term:
            return []
        candidates = self.client.get_candidate_pages(term, lang, max_candidates=self.MAX_CANDIDATES)
        found_images: List[Dict] = []
        for candidate in candidates:
            if len(found_images) >= limit:
                break
            try:
                page_data = self.client.fetch_page(lang=lang, candidate=candidate, props='pageimages|categories', extra_params={'piprop': 'original|thumbnail', 'pithumbsize': 640})
            except Exception:
                logger.exception('Error fetching page for images %s', candidate)
                continue
            if not page_data or page_data.get('missing'):
                continue
            if self.is_disambiguation_page(page_data):
                continue
            if self.is_list_or_index_page(page_data):
                continue
            original = page_data.get('original')
            if original and is_valid_image_url(original.get('source')):
                found_images.append({
                    'source': original.get('source'),
                    'width': original.get('width'),
                    'height': original.get('height'),
                    'title': page_data.get('title'),
                    'type': 'original'
                })
                continue
            thumbnail = page_data.get('thumbnail')
            if thumbnail and is_valid_image_url(thumbnail.get('source')):
                found_images.append({
                    'source': thumbnail.get('source'),
                    'width': thumbnail.get('width'),
                    'height': thumbnail.get('height'),
                    'title': page_data.get('title'),
                    'type': 'thumbnail'
                })
        return found_images
