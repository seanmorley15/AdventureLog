"""Admin for places and the visits, trails and activities recorded at them."""

from django.contrib import admin, messages
from adventures.models import Activity, Category, Location, Trail, Visit
from core.geo import has_coordinates
from core.admin import (
    TIMESTAMP_READONLY,
    UUID_READONLY,
    AdventureLogGeoModelAdmin,
    CoordinatesDisplayMixin,
    TimestampedAdminMixin,
    coordinate_display,
)


@admin.action(description='Trigger reverse geocoding for selected locations')
def trigger_geocoding(modeladmin, request, queryset):
    count = 0
    skipped = 0
    for location in queryset:
        if not has_coordinates(location.coordinates):
            skipped += 1
            continue
        try:
            location.save()
            count += 1
        except Exception as exc:
            modeladmin.message_user(
                request,
                f'Error geocoding {location}: {exc}',
                level=messages.ERROR,
            )
    if count:
        modeladmin.message_user(
            request,
            f'Geocoding triggered for {count} location(s).',
            level=messages.SUCCESS,
        )
    if skipped:
        modeladmin.message_user(
            request,
            f'Skipped {skipped} location(s) without coordinates.',
            level=messages.WARNING,
        )


class VisitInline(admin.TabularInline):
    model = Visit
    extra = 0
    fields = ('start_date', 'end_date', 'timezone', 'notes')
    show_change_link = True
    ordering = ('-start_date',)


class TrailInline(admin.TabularInline):
    model = Trail
    extra = 0
    fields = ('name', 'link', 'wanderer_id', 'wanderer_author_username')
    show_change_link = True


class ActivityInline(admin.TabularInline):
    model = Activity
    extra = 0
    fields = ('name', 'sport_type', 'distance', 'moving_time', 'start_date')
    show_change_link = True
    readonly_fields = fields
    can_delete = False
    max_num = 0


@admin.register(Location)
class LocationAdmin(CoordinatesDisplayMixin, AdventureLogGeoModelAdmin):
    list_display = (
        'name',
        'user',
        'category_display',
        'display_coordinates',
        'is_public',
        'visit_count',
        'city',
        'region',
        'country',
        'updated_at',
    )
    list_filter = ('is_public', 'user', 'category', 'country', 'region')
    search_fields = (
        'name',
        'location',
        'description',
        'tags',
        'user__username',
        'city__name',
        'region__name',
        'country__name',
    )
    list_select_related = ('user', 'category', 'city', 'region', 'country')
    autocomplete_fields = ('user', 'category', 'city', 'region', 'country')
    filter_horizontal = ('collections',)
    readonly_fields = (
        UUID_READONLY
        + TIMESTAMP_READONLY
        + ('display_coordinates_readonly', 'city', 'region', 'country')
    )
    actions = [trigger_geocoding]
    inlines = [VisitInline, TrailInline]
    date_hierarchy = 'updated_at'

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'user',
                    'name',
                    'category',
                    'location',
                    'description',
                    'tags',
                    'rating',
                    'price',
                    'link',
                    'is_public',
                    'collections',
                ),
            },
        ),
        (
            'Map',
            {
                'fields': ('coordinates', 'display_coordinates_readonly'),
                'description': 'Pick a point on the map. Saving triggers reverse geocoding when coordinates are set.',
            },
        ),
        (
            'Geocoded places',
            {
                'classes': ('collapse',),
                'fields': ('city', 'region', 'country'),
            },
        ),
        (
            'Metadata',
            {'classes': ('collapse',), 'fields': TIMESTAMP_READONLY},
        ),
    )

    @admin.display(description='Category')
    def category_display(self, obj):
        if not obj.category:
            return '—'
        icon = obj.category.icon or ''
        label = obj.category.display_name or obj.category.name
        return f'{label} {icon}'.strip()

    @admin.display(description='Visits', ordering='visits')
    def visit_count(self, obj):
        return obj.visits.count()

    @admin.display(description='Coordinates (lat, lon)')
    def display_coordinates_readonly(self, obj):
        return coordinate_display(obj.coordinates)


@admin.register(Visit)
class VisitAdmin(TimestampedAdminMixin, admin.ModelAdmin):
    list_display = ('location', 'start_date', 'end_date', 'timezone', 'activity_count')
    list_filter = ('timezone', 'location__user')
    search_fields = ('location__name', 'notes', 'location__user__username')
    autocomplete_fields = ('location',)
    date_hierarchy = 'start_date'
    inlines = [ActivityInline]
    readonly_fields = UUID_READONLY + TIMESTAMP_READONLY

    fieldsets = (
        (None, {'fields': ('location', 'start_date', 'end_date', 'timezone', 'notes')}),
        ('Metadata', {'classes': ('collapse',), 'fields': UUID_READONLY + TIMESTAMP_READONLY}),
    )

    @admin.display(description='Activities')
    def activity_count(self, obj):
        return obj.activities.count()


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'icon', 'name', 'user', 'location_count')
    list_filter = ('user',)
    search_fields = ('name', 'display_name', 'user__username')
    autocomplete_fields = ('user',)
    readonly_fields = UUID_READONLY

    @admin.display(description='Locations')
    def location_count(self, obj):
        return Location.objects.filter(category=obj).count()


@admin.register(Trail)
class TrailAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'user',
        'location',
        'wanderer_id',
        'has_link',
        'created_at',
    )
    list_filter = ('user',)
    search_fields = (
        'name',
        'link',
        'wanderer_id',
        'location__name',
        'user__username',
    )
    autocomplete_fields = ('user', 'location')
    readonly_fields = ('created_at',) + UUID_READONLY

    @admin.display(boolean=True, description='External link')
    def has_link(self, obj):
        return bool(obj.link)


class ActivityEndpointsDisplayMixin:
    @admin.display(description='Start')
    def display_start(self, obj):
        return coordinate_display(obj.start_point)

    @admin.display(description='End')
    def display_end(self, obj):
        return coordinate_display(obj.end_point)


@admin.register(Activity)
class ActivityAdmin(ActivityEndpointsDisplayMixin, AdventureLogGeoModelAdmin):
    list_display = (
        'name',
        'user',
        'visit',
        'sport_type',
        'distance',
        'elevation_gain',
        'moving_time',
        'display_start',
        'display_end',
    )
    list_filter = ('sport_type', 'user')
    search_fields = ('name', 'external_service_id', 'user__username', 'visit__location__name')
    autocomplete_fields = ('user', 'visit', 'trail')
    readonly_fields = UUID_READONLY + (
        'start_coords_readonly',
        'end_coords_readonly',
    )
    date_hierarchy = 'start_date'

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'user',
                    'visit',
                    'trail',
                    'name',
                    'sport_type',
                    'external_service_id',
                    'gpx_file',
                ),
            },
        ),
        (
            'Metrics',
            {
                'fields': (
                    'distance',
                    'moving_time',
                    'elapsed_time',
                    'rest_time',
                    'elevation_gain',
                    'elevation_loss',
                    'elev_high',
                    'elev_low',
                    'average_speed',
                    'max_speed',
                    'average_cadence',
                    'calories',
                ),
            },
        ),
        ('Schedule', {'fields': ('start_date', 'start_date_local', 'timezone')}),
        (
            'GPS endpoints',
            {
                'fields': (
                    'start_point',
                    'start_coords_readonly',
                    'end_point',
                    'end_coords_readonly',
                ),
            },
        ),
    )

    @admin.display(description='Start (lat, lon)')
    def start_coords_readonly(self, obj):
        return coordinate_display(obj.start_point)

    @admin.display(description='End (lat, lon)')
    def end_coords_readonly(self, obj):
        return coordinate_display(obj.end_point)
