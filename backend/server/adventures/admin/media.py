"""Admin for photos and attachments."""

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from adventures.models import ContentAttachment, ContentImage
from core.admin import UUID_READONLY, admin_image_preview, generic_object_admin_link


@admin.register(ContentType)
class ContentTypeAdmin(admin.ModelAdmin):
    search_fields = ('app_label', 'model')
    list_display = ('app_label', 'model')
    ordering = ('app_label', 'model')


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
