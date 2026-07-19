from django.apps import AppConfig


class PlacesConfig(AppConfig):
    """Overpass (OSM) place search with a local cache.

    Reuses the Overpass query/parse logic already implemented in
    `adventures.views.recommendations_view.RecommendationsViewSet` instead of
    reimplementing an Overpass client from scratch (see
    `places/overpass_client.py`). This app owns only the caching layer and
    the DRF endpoint on top of it.
    """

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'places'
