from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.sessions.models import Session
from allauth.account.decorators import secure_admin_login

from main.admin_utils import TIMESTAMP_READONLY, admin_image_preview
from users.models import APIKey, CustomUser

admin.site.login = secure_admin_login(admin.site.login)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = (
        'username',
        'email',
        'is_staff',
        'is_active',
        'public_profile',
        'measurement_system',
        'default_currency',
        'map_style',
        'profile_preview',
        'date_joined',
    )
    list_filter = (
        'is_staff',
        'is_active',
        'is_superuser',
        'public_profile',
        'measurement_system',
        'default_currency',
        'map_style',
    )
    search_fields = ('username', 'email', 'first_name', 'last_name', 'uuid')
    ordering = ('username',)
    readonly_fields = ('uuid', 'profile_preview_large', 'last_login', 'date_joined')
    filter_horizontal = ('groups', 'user_permissions')

    fieldsets = UserAdmin.fieldsets + (
        (
            'AdventureLog profile',
            {
                'fields': (
                    'profile_pic',
                    'profile_preview_large',
                    'uuid',
                    'public_profile',
                    'disable_password',
                    'measurement_system',
                    'default_currency',
                    'map_style',
                ),
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets

    @admin.display(description='Avatar')
    def profile_preview(self, obj):
        return admin_image_preview(obj.profile_pic, 40, 40)

    @admin.display(description='Profile picture')
    def profile_preview_large(self, obj):
        return admin_image_preview(obj.profile_pic, 120, 120)


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'user',
        'key_prefix',
        'created_at',
        'last_used_at',
    )
    list_filter = ('user',)
    search_fields = ('name', 'key_prefix', 'user__username')
    autocomplete_fields = ('user',)
    readonly_fields = ('id', 'key_prefix', 'key_hash', 'created_at', 'last_used_at')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('user', 'name')}),
        (
            'Key metadata',
            {
                'fields': ('id', 'key_prefix', 'key_hash', 'created_at', 'last_used_at'),
                'description': 'Plaintext API keys are only shown once at creation and are never stored.',
            },
        ),
    )

    def has_add_permission(self, request):
        return False


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'expire_date', 'session_preview')
    search_fields = ('session_key',)
    readonly_fields = ('session_key', 'expire_date', 'session_data_decoded')
    ordering = ('-expire_date',)

    @admin.display(description='Session data')
    def session_preview(self, obj):
        data = obj.get_decoded()
        preview = str(data)
        return preview[:80] + ('…' if len(preview) > 80 else '')

    @admin.display(description='Decoded session')
    def session_data_decoded(self, obj):
        return obj.get_decoded()
