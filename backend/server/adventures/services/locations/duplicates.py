"""Detect likely duplicate locations from name, address, and coordinates."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Iterable
from uuid import UUID

from django.db.models import Count

from adventures.models import Location
from adventures.utils.geo import point_to_lat_lon

NEAR_METERS = 150
CLOSE_METERS = 600
NEIGHBORHOOD_METERS = 3500
MAX_DISTANCE_METERS = 8000

NAME_ABBREVIATIONS = {
    'st': 'saint',
    'ste': 'saint',
    'saint': 'saint',
    'mt': 'mount',
    'mount': 'mount',
    'ft': 'fort',
    'fort': 'fort',
    'pk': 'park',
    'natl': 'national',
    'intl': 'international',
}

STOPWORDS = {
    'a',
    'an',
    'and',
    'at',
    'da',
    'de',
    'des',
    'di',
    'du',
    'el',
    'in',
    'la',
    'le',
    'of',
    'the',
    'van',
    'von',
}

GENERIC_TOKENS = {
    'airport',
    'bar',
    'bay',
    'beach',
    'bridge',
    'building',
    'cafe',
    'canyon',
    'cathedral',
    'center',
    'centre',
    'church',
    'city',
    'east',
    'falls',
    'forest',
    'garden',
    'general',
    'hill',
    'historic',
    'hotel',
    'house',
    'international',
    'island',
    'lake',
    'memorial',
    'mountain',
    'museum',
    'national',
    'new',
    'north',
    'park',
    'peak',
    'place',
    'point',
    'port',
    'public',
    'pub',
    'restaurant',
    'river',
    'road',
    'shop',
    'south',
    'square',
    'state',
    'station',
    'store',
    'street',
    'temple',
    'town',
    'trail',
    'valley',
    'west',
}

PLACEHOLDER_NAME_RE = re.compile(r'^(location at|-?\d+(\.\d+)?,\s*-?\d+)', re.IGNORECASE)

PUNCTUATION_RE = re.compile(r'[^a-z0-9\s]+')
WHITESPACE_RE = re.compile(r'\s+')


@dataclass(frozen=True)
class DuplicateMatch:
    location: Location
    score: float
    reasons: list[str] = field(default_factory=list)
    distance_meters: float | None = None

    def to_dict(self) -> dict:
        lat, lon = point_to_lat_lon(self.location.coordinates)
        category = None
        if self.location.category:
            category = {
                'id': str(self.location.category.id),
                'name': self.location.category.name,
                'display_name': self.location.category.display_name,
                'icon': self.location.category.icon,
            }
        return {
            'id': str(self.location.id),
            'name': self.location.name,
            'location': self.location.location,
            'latitude': lat,
            'longitude': lon,
            'category': category,
            'is_visited': bool(self.location.is_visited_status()),
            'visit_count': int(getattr(self.location, 'visit_count', self.location.visits.count())),
            'score': round(self.score, 4),
            'distance_meters': (
                round(self.distance_meters, 1) if self.distance_meters is not None else None
            ),
            'reasons': self.reasons,
        }


def _simple_stem(token: str) -> str:
    if len(token) > 4 and token.endswith('s') and not token.endswith('ss'):
        return token[:-1]
    return token


def normalize_place_name(name: str | None) -> str:
    text = (name or '').lower().replace("'", '').replace('’', '')
    text = PUNCTUATION_RE.sub(' ', text)
    tokens = []
    for raw in WHITESPACE_RE.sub(' ', text).split():
        token = NAME_ABBREVIATIONS.get(raw, raw)
        token = _simple_stem(token)
        if token and token not in STOPWORDS:
            tokens.append(token)
    return ' '.join(tokens)


def name_tokens(name: str | None) -> set[str]:
    normalized = normalize_place_name(name)
    return set(normalized.split()) if normalized else set()


def is_placeholder_name(name: str | None) -> bool:
    text = (name or '').strip()
    return not text or bool(PLACEHOLDER_NAME_RE.match(text))


def token_containment(left: str | None, right: str | None) -> float:
    """How completely the smaller distinctive token set sits inside the larger."""
    left_tokens = name_tokens(left)
    right_tokens = name_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0

    smaller, larger = (
        (left_tokens, right_tokens)
        if len(left_tokens) <= len(right_tokens)
        else (right_tokens, left_tokens)
    )
    distinctive = {token for token in smaller if token not in GENERIC_TOKENS and len(token) >= 4}
    if not distinctive:
        if len(smaller) < 2:
            return 0.0
        return len(smaller & larger) / len(smaller)

    overlap = distinctive & larger
    if not overlap:
        return 0.0
    if len(distinctive) == 1:
        token = next(iter(distinctive))
        # A single short token like "saint" would otherwise match every St/Saint place.
        return 1.0 if len(token) >= 6 else 0.0
    return len(overlap) / len(distinctive)


def string_ratio(left: str | None, right: str | None) -> float:
    a = (left or '').strip().lower()
    b = (right or '').strip().lower()
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def token_jaccard(left: str | None, right: str | None) -> float:
    left_tokens = name_tokens(left)
    right_tokens = name_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def name_similarity(left: str | None, right: str | None) -> float:
    raw = string_ratio(left, right)
    normalized_left = normalize_place_name(left)
    normalized_right = normalize_place_name(right)
    normalized = string_ratio(normalized_left, normalized_right)
    sorted_ratio = string_ratio(
        ' '.join(sorted(normalized_left.split())),
        ' '.join(sorted(normalized_right.split())),
    )
    return max(raw, normalized, sorted_ratio)


def haversine_meters(
    lat1: float | None,
    lon1: float | None,
    lat2: float | None,
    lon2: float | None,
) -> float | None:
    if None in (lat1, lon1, lat2, lon2):
        return None
    try:
        phi1 = math.radians(float(lat1))
        phi2 = math.radians(float(lat2))
        d_phi = math.radians(float(lat2) - float(lat1))
        d_lambda = math.radians(float(lon2) - float(lon1))
    except (TypeError, ValueError):
        return None

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 6371000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _parse_coordinate(value) -> float | None:
    if value in (None, ''):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed


def _both_have_coordinates(
    incoming_lat: float | None,
    incoming_lon: float | None,
    cand_lat: float | None,
    cand_lon: float | None,
) -> bool:
    return None not in (incoming_lat, incoming_lon, cand_lat, cand_lon)


def _score_candidate(
    *,
    incoming_name: str,
    incoming_location: str | None,
    incoming_lat: float | None,
    incoming_lon: float | None,
    candidate: Location,
) -> DuplicateMatch | None:
    cand_lat, cand_lon = point_to_lat_lon(candidate.coordinates)
    distance = haversine_meters(incoming_lat, incoming_lon, cand_lat, cand_lon)
    both_coords = _both_have_coordinates(incoming_lat, incoming_lon, cand_lat, cand_lon)

    if both_coords and distance is not None and distance > MAX_DISTANCE_METERS:
        return None

    placeholder = is_placeholder_name(incoming_name)
    name_score = 0.0 if placeholder else name_similarity(incoming_name, candidate.name)
    jaccard = 0.0 if placeholder else token_jaccard(incoming_name, candidate.name)
    containment = 0.0 if placeholder else token_containment(incoming_name, candidate.name)
    location_score = string_ratio(incoming_location, getattr(candidate, 'location', None))

    reasons: list[str] = []
    if name_score >= 0.82 or jaccard >= 0.55 or containment >= 0.8:
        reasons.append('similar_name')
    if distance is not None and distance <= CLOSE_METERS:
        reasons.append('nearby_coordinates')
    if incoming_location and candidate.location and location_score >= 0.78:
        reasons.append('similar_address')

    is_match = False
    if distance is not None and distance <= NEAR_METERS:
        is_match = True
        if 'nearby_coordinates' not in reasons:
            reasons.append('nearby_coordinates')
    elif not placeholder and (name_score >= 0.85 or jaccard >= 0.55 or containment >= 0.8):
        is_match = True
    elif distance is not None and distance <= CLOSE_METERS and (
        name_score >= 0.35 or jaccard >= 0.3 or containment >= 0.5
    ):
        is_match = True
    elif distance is not None and distance <= NEIGHBORHOOD_METERS and (
        name_score >= 0.65 or containment >= 0.7
    ):
        is_match = True
    elif location_score >= 0.82 and (name_score >= 0.5 or containment >= 0.6):
        is_match = True

    if not is_match:
        return None

    score = max(name_score, jaccard, containment, (name_score + location_score) / 2)
    if distance is not None:
        if distance <= NEAR_METERS:
            score = max(score, 0.97)
        elif distance <= CLOSE_METERS:
            score = min(1.0, score + 0.08)
        elif distance <= NEIGHBORHOOD_METERS:
            score = min(1.0, score + 0.04)

    return DuplicateMatch(
        location=candidate,
        score=score,
        reasons=reasons or ['similar_name'],
        distance_meters=distance,
    )


def _owned_locations(user, exclude_id: str | UUID | None = None) -> Iterable[Location]:
    queryset = (
        Location.objects.filter(user=user)
        .select_related('category')
        .annotate(visit_count=Count('visits'))
    )
    if exclude_id:
        queryset = queryset.exclude(id=exclude_id)
    return queryset


def find_duplicate_locations(
    user,
    *,
    name: str,
    latitude=None,
    longitude=None,
    location: str | None = None,
    exclude_id: str | UUID | None = None,
    limit: int = 5,
) -> list[DuplicateMatch]:
    incoming_name = (name or '').strip()
    incoming_lat = _parse_coordinate(latitude)
    incoming_lon = _parse_coordinate(longitude)
    if not incoming_name and (incoming_lat is None or incoming_lon is None):
        return []
    incoming_location = (location or '').strip() or None
    matches: list[DuplicateMatch] = []

    for candidate in _owned_locations(user, exclude_id=exclude_id):
        match = _score_candidate(
            incoming_name=incoming_name,
            incoming_location=incoming_location,
            incoming_lat=incoming_lat,
            incoming_lon=incoming_lon,
            candidate=candidate,
        )
        if match:
            matches.append(match)

    matches.sort(key=lambda item: item.score, reverse=True)
    return matches[: max(1, min(limit, 10))]


def find_best_duplicate_location(
    user,
    *,
    name: str,
    latitude=None,
    longitude=None,
    location: str | None = None,
    exclude_id: str | UUID | None = None,
) -> Location | None:
    matches = find_duplicate_locations(
        user,
        name=name,
        latitude=latitude,
        longitude=longitude,
        location=location,
        exclude_id=exclude_id,
        limit=1,
    )
    return matches[0].location if matches else None
