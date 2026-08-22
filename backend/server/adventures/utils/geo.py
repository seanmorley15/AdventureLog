"""Shared helpers for GeoDjango PointField (SRID 4326: x=longitude, y=latitude)."""

from __future__ import annotations

from typing import Any

from django.contrib.gis.geos import Point

WGS84_SRID = 4326


def make_point(lon: Any, lat: Any) -> Point | None:
    """Build a WGS84 point from longitude/latitude, or None if either is missing."""
    if lon is None or lat is None:
        return None
    try:
        return Point(float(lon), float(lat), srid=WGS84_SRID)
    except (TypeError, ValueError):
        return None


def point_to_lat_lon(point: Point | None) -> tuple[float | None, float | None]:
    """Return (latitude, longitude) from a Point, or (None, None)."""
    if not point:
        return None, None
    return point.y, point.x


def has_coordinates(point: Point | None) -> bool:
    return point is not None
