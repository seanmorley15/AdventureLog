"""Shared Django admin helpers for AdventureLog."""

from __future__ import annotations

from django.contrib import admin
from django.contrib.gis import admin as gis_admin
from django.utils.html import format_html

from adventures.utils.geo import point_to_lat_lon
from main.utils import build_media_url

TIMESTAMP_READONLY = ('created_at', 'updated_at')
UUID_READONLY = ('id',)


def coordinate_display(point, precision: int = 5) -> str:
    lat, lon = point_to_lat_lon(point)
    if lat is None or lon is None:
        return '—'
    return f'{lat:.{precision}f}, {lon:.{precision}f}'


def admin_image_preview(image_field, width: int = 100, height: int = 100):
    if not image_field:
        return '—'
    image_url = build_media_url(image_field.name)
    if not image_url:
        return '—'
    return format_html(
        '<img src="{}" width="{}" height="{}" style="object-fit:cover;border-radius:4px;" />',
        image_url,
        width,
        height,
    )


class TimestampedAdminMixin:
    readonly_fields = TIMESTAMP_READONLY


class AdventureLogGeoModelAdmin(gis_admin.GISModelAdmin):
    """GISModelAdmin with OSM map widgets for PointFields."""

    gis_widget_kwargs = {
        'attrs': {
            'default_lon': 0,
            'default_lat': 30,
            'default_zoom': 2,
        },
    }


class CoordinatesDisplayMixin:
    coordinates_field = 'coordinates'

    @admin.display(description='Coordinates')
    def display_coordinates(self, obj):
        return coordinate_display(getattr(obj, self.coordinates_field, None))

    @admin.display(description='Lat')
    def display_latitude(self, obj):
        lat, _ = point_to_lat_lon(getattr(obj, self.coordinates_field, None))
        return lat

    @admin.display(description='Lon')
    def display_longitude(self, obj):
        _, lon = point_to_lat_lon(getattr(obj, self.coordinates_field, None))
        return lon


class UserOwnedAdminMixin:
    list_filter = ('user',)
    autocomplete_fields = ('user',)
    search_fields = ('name',)


def generic_object_admin_link(obj, attr: str = 'item') -> str:
    linked = getattr(obj, attr, None)
    if not linked:
        return '—'
    try:
        from django.urls import reverse

        ct = obj.content_type
        admin_url = reverse(
            f'admin:{ct.app_label}_{ct.model}_change',
            args=[obj.object_id],
        )
        return format_html('<a href="{}">{}</a>', admin_url, str(linked))
    except Exception:
        return str(linked)
