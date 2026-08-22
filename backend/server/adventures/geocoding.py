"""Legacy geocoding compatibility shim.

The active implementation lives in providers, services, and shared utils.
This module only preserves old import paths during migration.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from django.conf import settings

from adventures.providers.geocoding.google import reverse_geocode as google_reverse_geocode
from adventures.providers.geocoding.osm import reverse_geocode as osm_reverse_geocode
from adventures.providers.places.google import search_places as google_search_places
from adventures.providers.places.osm import search_places as osm_search_places
from adventures.services.geocoding.reverse import reverse_geocode as reverse_geocode_service
from adventures.services.places.details import get_place_details as get_place_details_service
from adventures.services.places.search import search_places as search_places_service
from adventures.utils.geocoding_utils import (
    _extract_google_location_name,
    _extract_osm_location_name,
    _fetch_google_nearby_place_name,
    _parse_google_address_components,
    extractIsoCode,
)


@dataclass
class ProviderSearchResult:
    provider_used: Optional[str]
    providers_attempted: List[str] = field(default_factory=list)
    results: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None


def search_google(query):
    api_key = getattr(settings, "GOOGLE_MAPS_API_KEY", None)
    payload = google_search_places(query, api_key=api_key or "")
    if payload.error:
        return {"error": payload.error}
    return payload.data or []


def search_osm(query):
    payload = osm_search_places(query)
    if payload.error:
        return {"error": payload.error}
    return payload.data or []


def search_places(query):
    selection = search_places_service(query)
    if selection.error:
        return {"error": selection.error}
    return selection.results


def get_place_details(place_id, fallback_query=None, language='en'):
    return get_place_details_service(place_id, fallback_query=fallback_query, language=language)


def reverse_geocode(lat, lon, user):
    selection = reverse_geocode_service(lat, lon, user)
    return selection.data


def reverse_geocode_google(lat, lon, user):
    api_key = getattr(settings, "GOOGLE_MAPS_API_KEY", None)
    if not api_key:
        return {"error": "Geocoding service unavailable. Please check configuration."}

    payload = google_reverse_geocode(lat, lon, api_key)
    if payload.error:
        return {"error": payload.error}
    return payload.data or {}


def reverse_geocode_osm(lat, lon, user):
    payload = osm_reverse_geocode(lat, lon)
    if payload.error:
        return {"error": payload.error}
    return payload.data or {}


def search(query):
    """Legacy helper returning a list or error dict."""
    selection = search_places_service(query)
    if selection.error:
        return {"error": selection.error}
    return selection.results
