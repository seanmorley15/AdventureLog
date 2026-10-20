"""Admin for collections, their invites, and the day-by-day plan."""

from django.contrib import admin
from adventures.models import Collection, CollectionInvite, CollectionItineraryDay, CollectionItineraryItem
from core.admin import TIMESTAMP_READONLY, UUID_READONLY, TimestampedAdminMixin, generic_object_admin_link


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


@admin.register(Collection)
class CollectionAdmin(TimestampedAdminMixin, admin.ModelAdmin):
    list_display = (
        'name',
        'user',
        'type',
        'is_public',
        'is_archived',
        'start_date',
        'end_date',
        'location_count',
        'updated_at',
    )
    list_filter = ('type', 'is_public', 'is_archived', 'user')
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
                    'type',
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
