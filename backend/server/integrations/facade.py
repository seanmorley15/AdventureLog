"""
The one module the `adventures` app imports from `integrations`.

Keeping that dependency in one place means the rest of `adventures` never names an
integration model or service directly, and the direction stays one-way: integrations
may use `adventures`, and `adventures` reaches integrations only through here.
"""

from integrations.models import ImmichIntegration, WandererIntegration
from integrations.services.wanderer import (
    build_wanderer_trail_view_url,
    extract_wanderer_author_from_trail,
    fetch_trail_by_id,
    fetch_trail_geojson,
)

__all__ = [
    'ImmichIntegration',
    'build_wanderer_trail_view_url',
    'extract_wanderer_author_from_trail',
    'fetch_trail_by_id',
    'fetch_trail_geojson',
    'immich_integration_for',
    'immich_integrations_by_user',
    'wanderer_integration_for',
]


def immich_integration_for(user):
    """The user's Immich integration (a User or a user id), or None."""
    return ImmichIntegration.objects.filter(user=user).first()


def immich_integrations_by_user():
    """Every stored Immich integration, keyed by the id of the user it belongs to."""
    return {integration.user_id: integration for integration in ImmichIntegration.objects.all()}


def wanderer_integration_for(user):
    """The user's Wanderer integration, or None."""
    return WandererIntegration.objects.filter(user=user).first()
