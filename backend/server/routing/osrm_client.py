"""Thin HTTP client for a self-hosted OSRM `/table` service.

OSRM is the only source of driving distance/duration data in this project
(see blueprint invariant I1 — an LLM must never compute or invent a
geospatial fact). This module intentionally contains no ordering/optimization
logic — see `optimizer.py` for the pure algorithm that consumes the matrix
this module returns.

Reference: https://project-osrm.org (Table Service) and
docs/adr/001-infra-osrm.md for the capacity decision behind running this
self-hosted rather than against a managed routing API.
"""
from __future__ import annotations

import os

import requests

from .exceptions import OSRMUnavailableError

# OSRM's `/table` endpoint defaults to a 100-coordinate ceiling per request
# (`--max-table-size` on osrm-routed). A single itinerary day realistically
# has far fewer stops than that; if this limit is ever hit in practice, the
# fix is to page the request with `sources=`/`destinations=` query params,
# not to raise blindly as this module currently does.
OSRM_MAX_TABLE_SIZE = 100

DEFAULT_TIMEOUT_SECONDS = 10


def _osrm_base_url() -> str:
    """Read OSRM_URL from the environment.

    No default value on purpose: an unset OSRM_URL must mean "the
    optimization feature is unavailable", not "silently try localhost".
    """
    url = os.environ.get("OSRM_URL", "").strip()
    if not url:
        raise OSRMUnavailableError(
            "OSRM_URL não está configurada — a otimização de rota está indisponível."
        )
    return url.rstrip("/")


def get_duration_matrix(
    coordinates: list[tuple[float, float]],
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> list[list[float]]:
    """Call OSRM's `/table` service and return an NxN duration matrix (seconds).

    Args:
        coordinates: list of (latitude, longitude) pairs, in the order the
            caller wants them to appear in the returned matrix. Note OSRM's
            own HTTP API takes coordinates as longitude,latitude (reversed);
            that flip happens inside this function so every other module in
            this codebase can keep using (lat, lon), matching
            `Location.latitude`/`Location.longitude` field order.
        timeout: seconds to wait for OSRM before giving up.

    Returns:
        durations[i][j] = seconds to travel from coordinates[i] to
        coordinates[j] (may be asymmetric — OSRM returns real driving
        directions, not straight-line distance).

    Raises:
        OSRMUnavailableError: OSRM_URL is unset, more coordinates were
            requested than OSRM_MAX_TABLE_SIZE, the request failed to
            connect or timed out, or OSRM responded with a non-'Ok' status.
            Callers must catch this — see module docstring.
        ValueError: fewer than 2 coordinates were given (programmer error,
            not an infra failure, so it is not wrapped as OSRMUnavailableError).
    """
    if len(coordinates) < 2:
        raise ValueError("get_duration_matrix requires at least 2 coordinates")
    if len(coordinates) > OSRM_MAX_TABLE_SIZE:
        raise OSRMUnavailableError(
            f"{len(coordinates)} paradas excede o limite de {OSRM_MAX_TABLE_SIZE} "
            "coordenadas do OSRM /table (sem paginação via sources/destinations "
            "nesta implementação)."
        )

    base_url = _osrm_base_url()
    coord_str = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in coordinates)
    url = f"{base_url}/table/v1/driving/{coord_str}"

    try:
        response = requests.get(url, params={"annotations": "duration"}, timeout=timeout)
    except requests.RequestException as exc:
        raise OSRMUnavailableError(f"Falha ao conectar no OSRM ({base_url}): {exc}") from exc

    if response.status_code != 200:
        raise OSRMUnavailableError(f"OSRM retornou HTTP {response.status_code} para {url}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise OSRMUnavailableError(f"Resposta do OSRM não é JSON válido: {exc}") from exc

    if payload.get("code") != "Ok":
        raise OSRMUnavailableError(
            f"OSRM retornou código '{payload.get('code')}': {payload.get('message', '')}"
        )

    durations = payload.get("durations")
    if not durations or len(durations) != len(coordinates):
        raise OSRMUnavailableError("Matriz de durações do OSRM veio incompleta ou vazia.")

    return durations
