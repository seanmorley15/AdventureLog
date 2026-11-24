"""Admin for transportation, lodging, notes and checklists."""

from django.contrib import admin
from adventures.models import Checklist, ChecklistItem, Lodging, Note, Transportation
from core.admin import (
    TIMESTAMP_READONLY,
    UUID_READONLY,
    AdventureLogGeoModelAdmin,
    CoordinatesDisplayMixin,
    TimestampedAdminMixin,
    coordinate_display,
)


class ChecklistItemInline(admin.TabularInline):
    model = ChecklistItem
    extra = 1
    fields = ('name', 'is_checked', 'user')


class TransportEndpointsDisplayMixin:
    @admin.display(description='Origin')
    def display_origin(self, obj):
        return coordinate_display(obj.origin)

    @admin.display(description='Destination')
    def display_destination(self, obj):
        return coordinate_display(obj.destination)


@admin.register(Transportation)
class TransportationAdmin(
    TransportEndpointsDisplayMixin,
    AdventureLogGeoModelAdmin,
):
    list_display = (
        'name',
        'type',
        'user',
        'collection',
        'date',
        'display_origin',
        'display_destination',
        'is_public',
    )
    list_filter = ('type', 'is_public', 'user', 'collection')
    search_fields = (
        'name',
        'description',
        'from_location',
        'to_location',
        'flight_number',
        'user__username',
        'collection__name',
    )
    autocomplete_fields = ('user', 'collection')
    readonly_fields = UUID_READONLY + TIMESTAMP_READONLY + (
        'origin_coords_readonly',
        'destination_coords_readonly',
    )
    date_hierarchy = 'date'

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'user',
                    'collection',
                    'type',
                    'name',
                    'description',
                    'rating',
                    'price',
                    'link',
                    'is_public',
                ),
            },
        ),
        ('Schedule', {'fields': ('date', 'end_date', 'start_timezone', 'end_timezone')}),
        (
            'Route',
            {
                'fields': (
                    'from_location',
                    'to_location',
                    'start_code',
                    'end_code',
                    'flight_number',
                    'origin',
                    'origin_coords_readonly',
                    'destination',
                    'destination_coords_readonly',
                ),
            },
        ),
        ('Metadata', {'classes': ('collapse',), 'fields': UUID_READONLY + TIMESTAMP_READONLY}),
    )

    @admin.display(description='Origin (lat, lon)')
    def origin_coords_readonly(self, obj):
        return coordinate_display(obj.origin)

    @admin.display(description='Destination (lat, lon)')
    def destination_coords_readonly(self, obj):
        return coordinate_display(obj.destination)


@admin.register(Lodging)
class LodgingAdmin(CoordinatesDisplayMixin, AdventureLogGeoModelAdmin):
    list_display = (
        'name',
        'type',
        'user',
        'collection',
        'check_in',
        'check_out',
        'display_coordinates',
        'is_public',
    )
    list_filter = ('type', 'is_public', 'user', 'collection')
    search_fields = ('name', 'location', 'description', 'reservation_number', 'user__username')
    autocomplete_fields = ('user', 'collection')
    readonly_fields = UUID_READONLY + TIMESTAMP_READONLY + ('display_coordinates_readonly',)
    date_hierarchy = 'check_in'

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'user',
                    'collection',
                    'name',
                    'type',
                    'description',
                    'rating',
                    'price',
                    'link',
                    'reservation_number',
                    'is_public',
                ),
            },
        ),
        ('Stay', {'fields': ('check_in', 'check_out', 'timezone', 'location')}),
        (
            'Map',
            {'fields': ('coordinates', 'display_coordinates_readonly')},
        ),
        ('Metadata', {'classes': ('collapse',), 'fields': UUID_READONLY + TIMESTAMP_READONLY}),
    )

    @admin.display(description='Coordinates (lat, lon)')
    def display_coordinates_readonly(self, obj):
        return coordinate_display(obj.coordinates)


@admin.register(Note)
class NoteAdmin(TimestampedAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'user', 'collection', 'date', 'is_public', 'updated_at')
    list_filter = ('is_public', 'user', 'collection')
    search_fields = ('name', 'content', 'user__username')
    autocomplete_fields = ('user', 'collection')
    readonly_fields = UUID_READONLY + TIMESTAMP_READONLY
    date_hierarchy = 'date'


@admin.register(Checklist)
class ChecklistAdmin(TimestampedAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'user', 'collection', 'date', 'is_public', 'item_count')
    list_filter = ('is_public', 'user', 'collection')
    search_fields = ('name', 'user__username')
    autocomplete_fields = ('user', 'collection')
    readonly_fields = UUID_READONLY + TIMESTAMP_READONLY
    inlines = [ChecklistItemInline]

    @admin.display(description='Items')
    def item_count(self, obj):
        return ChecklistItem.objects.filter(checklist=obj).count()


@admin.register(ChecklistItem)
class ChecklistItemAdmin(TimestampedAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'checklist', 'user', 'is_checked')
    list_filter = ('is_checked', 'user', 'checklist')
    search_fields = ('name', 'checklist__name', 'user__username')
    autocomplete_fields = ('user', 'checklist')
    readonly_fields = UUID_READONLY + TIMESTAMP_READONLY
