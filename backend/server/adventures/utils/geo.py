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


def collection_center(collection) -> Point | None:
    """Geometric median of a collection's places: where most of them sit."""
    from django.contrib.gis.db.models.aggregates import Collect
    from django.contrib.gis.db.models.functions import Centroid, GeoFunc

    from adventures.models import Location

    class GeometricMedian(GeoFunc):
        function = 'ST_GeometricMedian'
        arity = 1

    points = Location.objects.filter(collections=collection, coordinates__isnull=False)
    if not points.exists():
        return None
    center = points.aggregate(center=GeometricMedian(Collect('coordinates')))['center']
    if center is None:
        center = points.aggregate(center=Centroid(Collect('coordinates')))['center']
    return center


def first_usable_lat_lon(*points: Point | None) -> tuple[float | None, float | None]:
    """Return the first (lat, lon) that is present and not Null Island (0, 0)."""
    for point in points:
        lat, lon = point_to_lat_lon(point)
        if lat is None or lon is None:
            continue
        if lat == 0 and lon == 0:
            continue
        return lat, lon
    return None, None


def parse_lon_lat(longitude: Any, latitude: Any) -> tuple[float | None, float | None]:
    """Parse a lon/lat pair, treating empty values and Null Island (0, 0) as missing."""
    if longitude in (None, '') or latitude in (None, ''):
        return None, None
    try:
        lon = round(float(longitude), 6)
        lat = round(float(latitude), 6)
    except (TypeError, ValueError):
        return None, None
    if lon == 0 and lat == 0:
        return None, None
    return lon, lat
