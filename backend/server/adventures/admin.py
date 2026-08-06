from django.contrib import admin, messages
from django.contrib.contenttypes.models import ContentType
from allauth.account.decorators import secure_admin_login

from adventures.models import (
    Activity,
    Category,
    Checklist,
    ChecklistItem,
    Collection,
    CollectionInvite,
    CollectionItineraryDay,
    CollectionItineraryItem,
    ContentAttachment,
    ContentImage,
    Location,
    Lodging,
    Note,
    Trail,
    Transportation,
    Visit,
)
from adventures.utils.geo import has_coordinates
from main.admin_utils import (
    TIMESTAMP_READONLY,
    UUID_READONLY,
    AdventureLogGeoModelAdmin,
    CoordinatesDisplayMixin,
    TimestampedAdminMixin,
    admin_image_preview,
    coordinate_display,
    generic_object_admin_link,
)

admin.site.login = secure_admin_login(admin.site.login)


@admin.register(ContentType)
class ContentTypeAdmin(admin.ModelAdmin):
    search_fields = ('app_label', 'model')
    list_display = ('app_label', 'model')
    ordering = ('app_label', 'model')


# ---------------------------------------------------------------------------
# Admin actions
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Inlines
# ---------------------------------------------------------------------------

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


class ChecklistItemInline(admin.TabularInline):
    model = ChecklistItem
    extra = 1
    fields = ('name', 'is_checked', 'user')


class CollectionInviteInline(admin.TabularInline):
    model = CollectionInvite
    extra = 0
    autocomplete_fields = ('invited_user',)
    readonly_fields = TIMESTAMP_READONLY


class CollectionItineraryDayInline(admin.TabularInline):
    model = CollectionItineraryDay
    extra = 0
    fields = ('date', 'name', 'description')
    ordering = ('date',)


# ---------------------------------------------------------------------------
# Adventures models
# ---------------------------------------------------------------------------

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


@admin.register(Collection)
class CollectionAdmin(TimestampedAdminMixin, admin.ModelAdmin):
    list_display = (
        'name',
        'user',
        'is_public',
        'is_archived',
        'start_date',
        'end_date',
        'location_count',
        'updated_at',
    )
    list_filter = ('is_public', 'is_archived', 'user')
    search_fields = ('name', 'description', 'user__username')
    autocomplete_fields = ('user', 'primary_image')
    filter_horizontal = ('shared_with',)
    readonly_fields = UUID_READONLY + TIMESTAMP_READONLY
    inlines = [CollectionInviteInline, CollectionItineraryDayInline]
    date_hierarchy = 'start_date'

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'user',
                    'name',
                    'description',
                    'link',
                    'is_public',
                    'is_archived',
                    'primary_image',
                ),
            },
        ),
        ('Dates', {'fields': ('start_date', 'end_date')}),
        ('Sharing', {'fields': ('shared_with',)}),
        ('Metadata', {'classes': ('collapse',), 'fields': UUID_READONLY + TIMESTAMP_READONLY}),
    )

    @admin.display(description='Locations')
    def location_count(self, obj):
        return obj.locations.count()


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


@admin.register(ContentImage)
class ContentImageAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'content_type',
        'content_link',
        'image_preview',
        'is_primary',
        'immich_id',
    )
    list_filter = ('content_type', 'is_primary', 'user')
    search_fields = ('immich_id', 'user__username', 'object_id')
    autocomplete_fields = ('user', 'content_type')
    readonly_fields = UUID_READONLY + ('image_preview_large', 'content_link')

    fieldsets = (
        (None, {'fields': ('user', 'content_type', 'object_id', 'content_link')}),
        ('Image', {'fields': ('image', 'image_preview_large', 'immich_id', 'is_primary')}),
    )

    @admin.display(description='Attached to')
    def content_link(self, obj):
        return generic_object_admin_link(obj, attr='content_object')

    @admin.display(description='Preview')
    def image_preview(self, obj):
        return admin_image_preview(obj.image, 48, 48)

    @admin.display(description='Preview')
    def image_preview_large(self, obj):
        return admin_image_preview(obj.image, 200, 200)


@admin.register(ContentAttachment)
class ContentAttachmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'content_type', 'content_link', 'file')
    list_filter = ('content_type', 'user')
    search_fields = ('name', 'user__username', 'object_id')
    autocomplete_fields = ('user', 'content_type')
    readonly_fields = UUID_READONLY + ('content_link',)

    @admin.display(description='Attached to')
    def content_link(self, obj):
        return generic_object_admin_link(obj, attr='content_object')


@admin.register(CollectionInvite)
class CollectionInviteAdmin(TimestampedAdminMixin, admin.ModelAdmin):
    list_display = ('collection', 'invited_user', 'created_at')
    search_fields = ('collection__name', 'invited_user__username')
    autocomplete_fields = ('collection', 'invited_user')
    readonly_fields = UUID_READONLY + TIMESTAMP_READONLY


@admin.register(CollectionItineraryItem)
class CollectionItineraryItemAdmin(admin.ModelAdmin):
    list_display = (
        'collection',
        'content_type',
        'object_link',
        'date',
        'is_global',
        'order',
        'created_at',
    )
    list_filter = ('content_type', 'is_global', 'collection')
    search_fields = ('collection__name',)
    autocomplete_fields = ('collection', 'content_type')
    readonly_fields = ('created_at',) + UUID_READONLY + ('object_link',)
    ordering = ('collection', 'date', 'order')

    fieldsets = (
        (None, {'fields': ('collection', 'content_type', 'object_id', 'object_link')}),
        ('Placement', {'fields': ('date', 'is_global', 'order')}),
        ('Metadata', {'classes': ('collapse',), 'fields': ('created_at',)}),
    )

    def object_link(self, obj):
        return generic_object_admin_link(obj, attr='item')

    object_link.short_description = 'Linked item'


@admin.register(CollectionItineraryDay)
class CollectionItineraryDayAdmin(TimestampedAdminMixin, admin.ModelAdmin):
    list_display = ('collection', 'date', 'name')
    list_filter = ('collection',)
    search_fields = ('collection__name', 'name', 'description')
    autocomplete_fields = ('collection',)
    readonly_fields = UUID_READONLY + TIMESTAMP_READONLY
    ordering = ('collection', 'date')


admin.site.site_header = 'AdventureLog Admin'
admin.site.site_title = 'AdventureLog Admin'
admin.site.index_title = 'AdventureLog administration'
