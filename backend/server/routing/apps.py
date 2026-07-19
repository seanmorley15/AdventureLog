from django.apps import AppConfig


class RoutingConfig(AppConfig):
    """Self-contained OSRM client + route-ordering algorithm.

    Deliberately has no models: it only talks to an external OSRM HTTP
    service (osrm_client.py) and rearranges indices of the matrix that
    service returns (optimizer.py). Domain glue (which Django models map to
    a geographic point, permission checks, persistence) lives in
    `adventures`, which imports from here — see
    `adventures/views/itinerary_view.py` and `adventures/utils/itinerary.py`.
    """

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'routing'
