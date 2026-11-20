"""A 0-100 score that ranks Google and OpenStreetMap places on the same scale."""

import math
from typing import Any, Dict

PRIOR_RATING = 4.0
PRIOR_WEIGHT = 20


def _quality(place: Dict[str, Any]) -> float:
    """0-60. Reviews for Google places, notability signals for OpenStreetMap ones."""
    rating = place.get('rating')
    if rating:
        n = place.get('review_count') or 0
        weighted = (rating * n + PRIOR_RATING * PRIOR_WEIGHT) / (n + PRIOR_WEIGHT)
        score = max(0.0, (weighted - 2.5) / 2.5) * 40  # 2.5 stars -> 0, 5 stars -> 40
        score += min(20.0, math.log10(n + 1) * 6) if n else 0.0
        return min(60.0, score)

    score = 0.0
    if place.get('wikidata') or place.get('wikipedia'):
        score += 30
    if place.get('website'):
        score += 8
    if place.get('opening_hours'):
        score += 6
    if place.get('photos'):
        score += 6
    if place.get('stars') or place.get('cuisine'):
        score += 5
    if place.get('address'):
        score += 5
    return min(60.0, score)


def _proximity(distance_km, radius_m: float) -> float:
    """0-30, falling off smoothly across the search radius."""
    if distance_km is None or not radius_m:
        return 15.0
    ratio = min(1.0, max(0.0, (distance_km * 1000.0) / radius_m))
    return 30.0 * (1.0 - ratio) ** 0.7


def _completeness(place: Dict[str, Any]) -> float:
    score = 0.0
    if place.get('photos'):
        score += 4
    if place.get('opening_hours'):
        score += 2
    if place.get('website') or place.get('phone_number'):
        score += 2
    if place.get('description'):
        score += 2
    return min(10.0, score)


def score_place(place: Dict[str, Any], radius_m: float) -> float:
    return round(_quality(place) + _proximity(place.get('distance_km'), radius_m) + _completeness(place), 2)
