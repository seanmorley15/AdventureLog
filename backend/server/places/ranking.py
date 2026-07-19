"""LLM ranking pipeline for stop suggestions (P5b).

Orchestrates: Overpass candidates (P5a, `places/services.py`) → sanitize
(strip geospatial facts) → LLM ranking (`places/llm_client.py`) → **I1
guard-rail** (every returned id must exist in the real candidate list;
anything else is discarded and logged, never shown) → attach real
travel time via OSRM (never the LLM — blueprint invariant I1).

This module is the one place invariant I1 is enforced end-to-end for the
suggestions feature: the LLM never receives, and is never asked to produce,
a distance, coordinate, or address-as-fact. See
`docs/hub/20-decisoes/003b-llm-provider.md` for the provider/model decision
and `docs/hub/30-planos/trilho-mvp-execucao.md` §P5b for the full spec.
"""
from __future__ import annotations

import logging

from routing import osrm_client
from routing.exceptions import OSRMUnavailableError

from . import llm_client, services
from .exceptions import LLMUnavailableError

logger = logging.getLogger(__name__)

# Fields sent to the LLM. Deliberately excludes latitude/longitude/
# distance_km/address — the LLM never sees a geospatial fact (I1).
_SANITIZED_FIELDS = ('id', 'name', 'cuisine', 'wheelchair', 'fee', 'opening_hours', 'description')


def _sanitize_candidate(candidate: dict) -> dict:
    sanitized = {field: candidate.get(field) for field in _SANITIZED_FIELDS}
    sanitized['category'] = candidate.get('primary_type')
    return sanitized


def _attach_travel_seconds(stop_lat, stop_lon, suggestions: list[dict]) -> None:
    """Best-effort: attach real driving time from the stop to each suggestion
    via OSRM. Mutates `suggestions` in place. Never touches the LLM — if OSRM
    is unavailable, every suggestion just gets `travel_seconds: None` (I4:
    degrade gracefully, don't fail the whole request)."""
    geolocated = [s for s in suggestions if s.get('latitude') is not None and s.get('longitude') is not None]
    for s in suggestions:
        s['travel_seconds'] = None

    if not geolocated:
        return

    coordinates = [(stop_lat, stop_lon)] + [(s['latitude'], s['longitude']) for s in geolocated]
    try:
        durations = osrm_client.get_duration_matrix(coordinates)
    except OSRMUnavailableError:
        return

    origin_row = durations[0]
    for index, suggestion in enumerate(geolocated, start=1):
        suggestion['travel_seconds'] = origin_row[index]


def suggest_places(location, category: str, radius, restrictions: str) -> dict:
    """Full pipeline: candidates → LLM ranking → I1 guard-rail → travel time.

    Args:
        location: an `adventures.models.Location` with latitude/longitude.
        category: one of `places.overpass_client.VALID_CATEGORIES`.
        radius: search radius in meters (same contract as
            `services.get_nearby_places`).
        restrictions: free-text user restrictions (diet, budget,
            accessibility, etc.) forwarded to the LLM as context only.

    Returns:
        {"error": str|None, "suggestions": list[dict]} — each suggestion is
        the full original candidate dict (with real lat/lon/distance from
        Overpass) plus "justification" (LLM text) and "travel_seconds"
        (OSRM, or None if OSRM unavailable). Every "id" in the output is
        guaranteed to have come from the real candidate list.
    """
    candidates_result = services.get_nearby_places(location.latitude, location.longitude, radius, category)

    if candidates_result.get('error') and not candidates_result.get('results'):
        return {'error': candidates_result['error'], 'suggestions': []}

    candidates = candidates_result.get('results', [])
    if not candidates:
        return {'error': None, 'suggestions': []}

    candidates_by_id = {c['id']: c for c in candidates if c.get('id')}
    sanitized_payload = [_sanitize_candidate(c) for c in candidates]

    try:
        raw_suggestions = llm_client.rank_candidates(sanitized_payload, restrictions)
    except LLMUnavailableError as exc:
        return {'error': str(exc), 'suggestions': []}

    validated_suggestions = []
    for raw in raw_suggestions:
        candidate_id = raw.get('id') if isinstance(raw, dict) else None
        candidate = candidates_by_id.get(candidate_id)
        if candidate is None:
            logger.warning('places.ranking: LLM devolveu id fora do input, descartado: %r', candidate_id)
            continue
        validated_suggestions.append({**candidate, 'justification': raw.get('justification', '')})

    _attach_travel_seconds(location.latitude, location.longitude, validated_suggestions)

    return {'error': None, 'suggestions': validated_suggestions}
