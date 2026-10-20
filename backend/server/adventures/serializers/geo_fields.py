"""DRF fields that expose latitude/longitude while storing GeoDjango PointFields."""

from __future__ import annotations

from rest_framework import serializers

from core.geo import make_point, point_to_lat_lon


def _register_declared_fields(cls, names: tuple[str, ...]) -> None:
    """
    DRF only collects fields from Serializer subclasses into _declared_fields.
    Mixins must register explicitly so Meta.fields names are not built from the model.
    """
    declared = getattr(cls, '_declared_fields', None)
    if declared is None:
        return
    for name in names:
        declared[name] = serializers.FloatField(required=False, allow_null=True)


def _apply_point(
    validated_data: dict,
    lat_key: str,
    lon_key: str,
    point_key: str,
    message: str,
    error_key: str | None = None,
) -> dict:
    """
    Replace a latitude/longitude pair in ``validated_data`` with one point.

    Nothing sent leaves the data alone, both null clears the point, and one without the
    other is an error. ``error_key`` names the field the error is reported against;
    without it the error is not tied to a field.
    """
    lat = validated_data.pop(lat_key, serializers.empty)
    lon = validated_data.pop(lon_key, serializers.empty)
    if lat is serializers.empty and lon is serializers.empty:
        return validated_data
    lat = None if lat is serializers.empty else lat
    lon = None if lon is serializers.empty else lon
    if lat is None and lon is None:
        validated_data[point_key] = None
        return validated_data

    point = make_point(lon, lat)
    if point is None:
        raise serializers.ValidationError({error_key: message} if error_key else message)
    validated_data[point_key] = point
    return validated_data


class _PointFieldsMixin:
    """Registers the declared lat/lon fields; subclasses list them in ``_geo_field_names``."""

    _geo_field_names: tuple[str, ...] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        _register_declared_fields(cls, cls._geo_field_names)


class CoordinateSerializerMixin(_PointFieldsMixin):
    """
    Mixin for serializers with a single `coordinates` PointField on the model.

    Declares writable `latitude` and `longitude` on the serializer; maps them to
    `coordinates` in validated_data before create/update.
    """

    _geo_field_names = ('latitude', 'longitude')
    _point_field_name = 'coordinates'

    def _get_point_field_name(self) -> str:
        return getattr(self, '_point_field_name', 'coordinates')

    def _pop_lat_lon(self, validated_data: dict) -> dict:
        return _apply_point(
            validated_data,
            'latitude',
            'longitude',
            self._get_point_field_name(),
            'Valid latitude and longitude are required together.',
        )

    def create(self, validated_data):
        validated_data = self._pop_lat_lon(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._pop_lat_lon(validated_data)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        point = getattr(instance, self._get_point_field_name(), None)
        lat, lon = point_to_lat_lon(point)
        data['latitude'] = lat
        data['longitude'] = lon
        return data


class TransportationCoordinateMixin(_PointFieldsMixin):
    """Maps origin/destination lat-lon API fields to PointFields on Transportation."""

    _geo_field_names = ('origin_latitude', 'origin_longitude', 'destination_latitude', 'destination_longitude')

    def _pop_transport_points(self, validated_data: dict) -> dict:
        message = 'Valid latitude and longitude are required together.'
        validated_data = _apply_point(
            validated_data, 'origin_latitude', 'origin_longitude', 'origin', message, 'origin_latitude'
        )
        return _apply_point(
            validated_data,
            'destination_latitude',
            'destination_longitude',
            'destination',
            message,
            'destination_latitude',
        )

    def create(self, validated_data):
        validated_data = self._pop_transport_points(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._pop_transport_points(validated_data)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        o_lat, o_lon = point_to_lat_lon(getattr(instance, 'origin', None))
        d_lat, d_lon = point_to_lat_lon(getattr(instance, 'destination', None))
        data['origin_latitude'] = o_lat
        data['origin_longitude'] = o_lon
        data['destination_latitude'] = d_lat
        data['destination_longitude'] = d_lon
        return data


class ActivityCoordinateMixin(_PointFieldsMixin):
    """Maps start/end lat-lng API fields to PointFields on Activity."""

    _geo_field_names = ('start_lat', 'start_lng', 'end_lat', 'end_lng')

    def _pop_activity_points(self, validated_data: dict) -> dict:
        message = 'Valid start/end coordinates are required together.'
        validated_data = _apply_point(validated_data, 'start_lat', 'start_lng', 'start_point', message, 'start_lat')
        return _apply_point(validated_data, 'end_lat', 'end_lng', 'end_point', message, 'end_lat')

    def create(self, validated_data):
        validated_data = self._pop_activity_points(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._pop_activity_points(validated_data)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        s_lat, s_lng = point_to_lat_lon(getattr(instance, 'start_point', None))
        e_lat, e_lng = point_to_lat_lon(getattr(instance, 'end_point', None))
        data['start_lat'] = s_lat
        data['start_lng'] = s_lng
        data['end_lat'] = e_lat
        data['end_lng'] = e_lng
        return data
