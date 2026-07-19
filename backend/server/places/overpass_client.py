"""Overpass client for the `places` app.

Deliberately does NOT reimplement Overpass query-building/parsing: that logic
already lives in `adventures.views.recommendations_view.RecommendationsViewSet`
(query construction per category, response parsing, quality score). This
module subclasses it purely to swap the `User-Agent` header to one that
identifies Trilho specifically (CODEMAP/blueprint requirement), and exposes a
plain function so callers outside the DRF view layer (the cache service)
don't need to touch a ViewSet.
"""
from adventures.views.recommendations_view import RecommendationsViewSet

VALID_CATEGORIES = ('tourism', 'food', 'lodging')


class _TrilhoOverpassClient(RecommendationsViewSet):
    HEADERS = {'User-Agent': 'Trilho/0.1 (uso pessoal; contato no repo)'}


def fetch_nearby(lat, lon, radius, category):
    """Query Overpass for `category` around (lat, lon) within `radius` meters.

    Returns {"error": str|None, "results": list[dict]} — same shape as
    RecommendationsViewSet.query_overpass, which already handles timeout,
    HTTP errors and malformed JSON without raising (so a network hiccup
    returns a controlled error, not a 500 — DoD of 5a.2).
    """
    client = _TrilhoOverpassClient()
    return client.query_overpass(lat, lon, radius, category, request=None)
