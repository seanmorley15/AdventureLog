from typing import Optional
from urllib.parse import quote

import requests
from django.conf import settings

from adventures.providers.base import ProviderResult
from adventures.services.external_cache import get_or_fetch_cached

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
            url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{encoded_query}"
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
