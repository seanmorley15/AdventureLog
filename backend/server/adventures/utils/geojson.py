import io

import geojson
import gpxpy


def _gpx_to_feature_collection(gpx):
    features = []
    for track in gpx.tracks:
        track_name = track.name or 'GPX Track'
        for segment in track.segments:
            coords = [(point.longitude, point.latitude) for point in segment.points]
            if coords:
                feature = geojson.Feature(
                    geometry=geojson.LineString(coords),
                    properties={'name': track_name},
                )
                features.append(feature)

    return geojson.FeatureCollection(features)


def gpx_bytes_to_geojson(gpx_content: bytes):
    """
    Convert raw GPX bytes to GeoJSON FeatureCollection.

    Returns None if content is empty, FeatureCollection if successful,
    or an error dict on parse failure.
    """
    if not gpx_content:
        return None

    try:
        gpx = gpxpy.parse(io.BytesIO(gpx_content))
        return _gpx_to_feature_collection(gpx)
    except Exception as exc:
        return {
            'error': str(exc),
            'message': 'Failed to convert GPX to GeoJSON',
        }


def gpx_to_geojson(gpx_file):
    """
    Convert a GPX file to GeoJSON format.

    Args:
        gpx_file: Django FileField or file-like object containing GPX data

    Returns:
        dict: GeoJSON FeatureCollection, None, or error dict
    """
    if not gpx_file:
        return None

    try:
        with gpx_file.open('r') as f:
            gpx = gpxpy.parse(f)
        return _gpx_to_feature_collection(gpx)
    except Exception as exc:
        return {
            'error': str(exc),
            'message': 'Failed to convert GPX to GeoJSON',
        }


GPX_GEOJSON_CACHE_PREFIX = 'gpx_geojson_v1'
GPX_GEOJSON_CACHE_TIMEOUT = 60 * 60 * 24 * 7


def cached_gpx_geojson(gpx_file):
    """
    ``gpx_to_geojson`` with a cache keyed by the stored file name.

    Upload names are random (see ``PathAndRename``), so a name never points at
    different content and nothing needs invalidating. Only the derived GeoJSON is
    cached; access to the file itself is still decided by the caller. Errors are
    not cached, and a cache failure (including an item too large for memcached)
    just means the file is parsed again next time.
    """
    if not gpx_file:
        return None
    name = getattr(gpx_file, 'name', None)
    if not name:
        return gpx_to_geojson(gpx_file)

    from core.cache import build_cache_key
    from django.core.cache import cache

    key = build_cache_key(GPX_GEOJSON_CACHE_PREFIX, name)
    try:
        cached = cache.get(key)
        if cached is not None:
            return cached
    except Exception:
        cached = None

    result = gpx_to_geojson(gpx_file)
    if result is not None and not (isinstance(result, dict) and result.get('error')):
        try:
            cache.set(key, result, GPX_GEOJSON_CACHE_TIMEOUT)
        except Exception:
            pass
    return result


GPX_DISTANCE_CACHE_PREFIX = 'gpx_distance_v1'


def cached_gpx_distance_km(gpx_file, compute):
    """
    ``compute(gpx_file)`` (a distance in km, or None) cached by the stored file name.

    Same reasoning as ``cached_gpx_geojson``: upload names are random, so a name never
    points at different content. A failed parse (None) is not cached.
    """
    name = getattr(gpx_file, 'name', None)
    if not name:
        return compute(gpx_file)

    from core.cache import build_cache_key
    from django.core.cache import cache

    key = build_cache_key(GPX_DISTANCE_CACHE_PREFIX, name)
    try:
        cached = cache.get(key)
        if cached is not None:
            return cached
    except Exception:
        pass

    result = compute(gpx_file)
    if result is not None:
        try:
            cache.set(key, result, GPX_GEOJSON_CACHE_TIMEOUT)
        except Exception:
            pass
    return result
