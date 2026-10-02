from typing import Any, Dict, Optional

from django.conf import settings

from adventures.providers.places.google import fetch_place_details, search_places
from adventures.services.places.details import _compose_place_description


def _display_name(place: Dict[str, Any]) -> str:
    display = place.get("displayName") or {}
    if isinstance(display, dict):
        return (display.get("text") or "").strip()
    return str(display or "").strip()


def _score_place(place: Dict[str, Any], query: str) -> int:
    name = _display_name(place).lower()
    query_l = query.lower()
    score = 0
    if name == query_l:
        score += 4
    elif query_l in name or name in query_l:
        score += 2
    editorial = ((place.get("editorialSummary") or {}).get("text") or "").strip()
    if editorial:
        score += 3
    if place.get("id"):
        score += 1
    return score


def _payload_from_place(place: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    editorial_summary = ((place.get("editorialSummary") or {}).get("text") or "").strip()
    reviews = place.get("reviews") or []
    review_snippets = [((review.get("text") or {}).get("text")) for review in reviews]
    extract = _compose_place_description(editorial_summary, review_snippets)
    if not extract:
        return None
    return {
        "extract": extract,
        "title": _display_name(place) or None,
        "source": "google",
    }


def fetch_google_description(name: str, place_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    api_key = getattr(settings, "GOOGLE_MAPS_API_KEY", "") or ""
    if not api_key.strip():
        raise RuntimeError("google_maps_disabled")

    query = (name or "").strip()
    if place_id:
        details = fetch_place_details(place_id, api_key)
        if not details.error and details.data:
            payload = _payload_from_place(details.data)
            if payload:
                return payload

    if not query:
        return None

    search = search_places(query, api_key, max_results=8)
    if search.error or not search.data:
        return None

    ranked = sorted(search.data, key=lambda place: _score_place(place, query), reverse=True)
    best = ranked[0] if ranked else None
    if not best:
        return None

    payload = _payload_from_place(best)
    if payload:
        return payload

    best_id = best.get("id")
    if not best_id:
        return None

    details = fetch_place_details(best_id, api_key)
    if details.error or not details.data:
        return None
    return _payload_from_place(details.data)
