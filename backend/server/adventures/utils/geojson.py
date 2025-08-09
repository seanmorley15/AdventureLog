import gpxpy
import geojson

def gpx_to_geojson(gpx_file):
    """
    Convert a GPX file to GeoJSON format.

    Args:
        gpx_file: Django FileField or file-like object containing GPX data

    Returns:
        dict: GeoJSON FeatureCollection or error dict
    """
    if not gpx_file:
        return None

    try:
        with gpx_file.open('r') as f:
            gpx = gpxpy.parse(f)

        features = []
        for track in gpx.tracks:
            track_name = track.name or "GPX Track"
            for segment in track.segments:
                coords = [(point.longitude, point.latitude) for point in segment.points]
                if coords:
                    feature = geojson.Feature(
                        geometry=geojson.LineString(coords),
                        properties={"name": track_name}
                    )
                    features.append(feature)

        return geojson.FeatureCollection(features)

    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to convert GPX to GeoJSON"
        }