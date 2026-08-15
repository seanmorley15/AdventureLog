"""DRF fields that expose latitude/longitude while storing GeoDjango PointFields."""

from __future__ import annotations

from rest_framework import serializers

from adventures.utils.geo import make_point, point_to_lat_lon


def _register_declared_fields(cls, field_map: dict[str, serializers.Field]) -> None:
    """
    DRF only collects fields from Serializer subclasses into _declared_fields.
    Mixins must register explicitly so Meta.fields names are not built from the model.
    """
    declared = getattr(cls, '_declared_fields', None)
    if declared is None:
        return
    for name, field in field_map.items():
        declared[name] = field


class CoordinateSerializerMixin:
    """
    Mixin for serializers with a single `coordinates` PointField on the model.

    Declares writable `latitude` and `longitude` on the serializer; maps them to
    `coordinates` in validated_data before create/update.
    """

    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    _point_field_name = 'coordinates'

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        _register_declared_fields(
            cls,
            {
                'latitude': serializers.FloatField(required=False, allow_null=True),
                'longitude': serializers.FloatField(required=False, allow_null=True),
            },
        )

    def _get_point_field_name(self) -> str:
        return getattr(self, '_point_field_name', 'coordinates')

    def _pop_lat_lon(self, validated_data: dict) -> dict:
        lat = validated_data.pop('latitude', serializers.empty)
        lon = validated_data.pop('longitude', serializers.empty)
        if lat is serializers.empty and lon is serializers.empty:
            return validated_data
        lat = None if lat is serializers.empty else lat
        lon = None if lon is serializers.empty else lon
        if lat is None and lon is None:
            validated_data[self._get_point_field_name()] = None
        else:
            point = make_point(lon, lat)
            if point is None and (lat is not None or lon is not None):
                raise serializers.ValidationError(
                    'Valid latitude and longitude are required together.'
                )
            validated_data[self._get_point_field_name()] = point
        return validated_data

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


class TransportationCoordinateMixin:
    """Maps origin/destination lat-lon API fields to PointFields on Transportation."""

    origin_latitude = serializers.FloatField(required=False, allow_null=True)
    origin_longitude = serializers.FloatField(required=False, allow_null=True)
    destination_latitude = serializers.FloatField(required=False, allow_null=True)
    destination_longitude = serializers.FloatField(required=False, allow_null=True)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        _register_declared_fields(
            cls,
            {
                'origin_latitude': serializers.FloatField(required=False, allow_null=True),
                'origin_longitude': serializers.FloatField(required=False, allow_null=True),
                'destination_latitude': serializers.FloatField(required=False, allow_null=True),
                'destination_longitude': serializers.FloatField(required=False, allow_null=True),
            },
        )

    def _apply_endpoint(
        self,
        validated_data: dict,
        lat_key: str,
        lon_key: str,
        point_key: str,
    ) -> dict:
        lat = validated_data.pop(lat_key, serializers.empty)
        lon = validated_data.pop(lon_key, serializers.empty)
        if lat is serializers.empty and lon is serializers.empty:
            return validated_data
        lat = None if lat is serializers.empty else lat
        lon = None if lon is serializers.empty else lon
        if lat is None and lon is None:
            validated_data[point_key] = None
        else:
            point = make_point(lon, lat)
            if point is None and (lat is not None or lon is not None):
                raise serializers.ValidationError(
                    {lat_key: 'Valid latitude and longitude are required together.'}
                )
            validated_data[point_key] = point
        return validated_data

    def _pop_transport_points(self, validated_data: dict) -> dict:
        validated_data = self._apply_endpoint(
            validated_data, 'origin_latitude', 'origin_longitude', 'origin'
        )
        validated_data = self._apply_endpoint(
            validated_data,
            'destination_latitude',
            'destination_longitude',
            'destination',
        )
        return validated_data

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


class ActivityCoordinateMixin:
    """Maps start/end lat-lng API fields to PointFields on Activity."""

    start_lat = serializers.FloatField(required=False, allow_null=True)
    start_lng = serializers.FloatField(required=False, allow_null=True)
    end_lat = serializers.FloatField(required=False, allow_null=True)
    end_lng = serializers.FloatField(required=False, allow_null=True)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        _register_declared_fields(
            cls,
            {
                'start_lat': serializers.FloatField(required=False, allow_null=True),
                'start_lng': serializers.FloatField(required=False, allow_null=True),
                'end_lat': serializers.FloatField(required=False, allow_null=True),
                'end_lng': serializers.FloatField(required=False, allow_null=True),
            },
        )

    def _apply_activity_endpoint(
        self,
        validated_data: dict,
        lat_key: str,
        lng_key: str,
        point_key: str,
    ) -> dict:
        lat = validated_data.pop(lat_key, serializers.empty)
        lng = validated_data.pop(lng_key, serializers.empty)
        if lat is serializers.empty and lng is serializers.empty:
            return validated_data
        lat = None if lat is serializers.empty else lat
        lng = None if lng is serializers.empty else lng
        if lat is None and lng is None:
            validated_data[point_key] = None
        else:
            point = make_point(lng, lat)
            if point is None and (lat is not None or lng is not None):
                raise serializers.ValidationError(
                    {lat_key: 'Valid start/end coordinates are required together.'}
                )
            validated_data[point_key] = point
        return validated_data

    def _pop_activity_points(self, validated_data: dict) -> dict:
        validated_data = self._apply_activity_endpoint(
            validated_data, 'start_lat', 'start_lng', 'start_point'
        )
        validated_data = self._apply_activity_endpoint(
            validated_data, 'end_lat', 'end_lng', 'end_point'
        )
        return validated_data

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
