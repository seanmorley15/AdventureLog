"""Where a collection's places are centred."""

from django.contrib.gis.db.models.aggregates import Collect
from django.contrib.gis.db.models.functions import Centroid, GeoFunc
from django.contrib.gis.geos import Point

from adventures.models import Location


class GeometricMedian(GeoFunc):
    function = 'ST_GeometricMedian'
    arity = 1


def collection_center(collection) -> Point | None:
    """Geometric median of a collection's places: where most of them sit."""
    points = Location.objects.filter(collections=collection, coordinates__isnull=False)
    if not points.exists():
        return None
    center = points.aggregate(center=GeometricMedian(Collect('coordinates')))['center']
    if center is None:
        center = points.aggregate(center=Centroid(Collect('coordinates')))['center']
    return center
