class OSRMUnavailableError(Exception):
    """Raised whenever the OSRM service cannot be used: not configured
    (OSRM_URL unset), unreachable, timed out, or returned an error response.

    Callers (Django views) MUST catch this and degrade gracefully — per the
    Trilho blueprint invariant I4, OSRM being down can never take the rest
    of the API down with it. The correct response is "optimize feature
    unavailable", not a 500.
    """

    pass
