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
