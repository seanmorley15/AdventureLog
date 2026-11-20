"""Collapse the same place reported by Google and OpenStreetMap into one result."""

import math
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Dict, List

MAX_DISTANCE_M = 75
NAME_RATIO = 0.82


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def normalize_name(name: str) -> str:
    text = unicodedata.normalize('NFKD', name or '')
    text = ''.join(c for c in text if not unicodedata.combining(c)).casefold()
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', ' ', text)).strip()


def names_match(a: str, b: str) -> bool:
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return False
    if na == nb or na in nb or nb in na:
        return True
    return SequenceMatcher(None, na, nb).ratio() > NAME_RATIO


def is_same_place(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    try:
        close = haversine_m(a['latitude'], a['longitude'], b['latitude'], b['longitude']) < MAX_DISTANCE_M
    except (KeyError, TypeError, ValueError):
        return False
    return close and names_match(a.get('name', ''), b.get('name', ''))


def _fill(primary: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(primary)
    for key, value in extra.items():
        if key in ('id', 'external_id', 'source', 'sources', 'quality_score'):
            continue
        if merged.get(key) in (None, '', []) and value not in (None, '', []):
            merged[key] = value
    merged['sources'] = sorted({*primary.get('sources', [primary.get('source')]), *extra.get('sources', [extra.get('source')])})
    return merged


def merge_results(google_results: List[Dict[str, Any]], osm_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Google results win; matching OSM places only fill gaps in them."""
    merged = [dict(g, sources=['google']) for g in google_results]
    for osm in osm_results:
        osm = dict(osm, sources=['osm'])
        for i, g in enumerate(merged):
            if is_same_place(g, osm):
                merged[i] = _fill(g, osm)
                break
        else:
            merged.append(osm)
    return merged
