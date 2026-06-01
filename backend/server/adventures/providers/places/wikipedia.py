from typing import Optional
from urllib.parse import quote

import requests

from adventures.providers.base import ProviderResult


def fetch_summary(query: str, language: str = "en") -> ProviderResult[Optional[str]]:
    normalized_query = (query or "").strip()
    if not normalized_query:
        return ProviderResult(error="Missing query")

    candidates = [normalized_query]
    if "," in normalized_query:
        head = normalized_query.split(",")[0].strip()
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
                return ProviderResult(data=extract)
        except requests.exceptions.RequestException:
            continue

    return ProviderResult(data=None)
