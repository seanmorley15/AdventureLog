from django.contrib import admin
from allauth.account.decorators import secure_admin_login

from integrations.models import ImmichIntegration, StravaToken, WandererIntegration

admin.site.login = secure_admin_login(admin.site.login)

@admin.register(WandererIntegration)
class WandererIntegrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'server_url', 'id')
    search_fields = ('user__username', 'server_url')
    autocomplete_fields = ('user',)
    readonly_fields = ('id',)

    fieldsets = (
        (None, {'fields': ('user', 'server_url', 'id')}),
        (
            'Credentials',
            {
                'classes': ('collapse',),
                'fields': ('api_key',),
                'description': 'API key is not shown in list views. Expand to view or rotate.',
            },
        ),
    )


@admin.register(ImmichIntegration)
class ImmichIntegrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'server_url', 'copy_locally', 'id')
    list_filter = ('copy_locally',)
    search_fields = ('user__username', 'server_url')
    autocomplete_fields = ('user',)
    readonly_fields = ('id',)

    fieldsets = (
        (None, {'fields': ('user', 'server_url', 'copy_locally', 'id')}),
        (
            'Credentials',
            {'classes': ('collapse',), 'fields': ('api_key',)},
        ),
    )


@admin.register(StravaToken)
class StravaTokenAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'athlete_id',
        'expires_at',
        'scope',
        'updated_at',
    )
    list_filter = ('scope',)
    search_fields = ('user__username', 'athlete_id')
    autocomplete_fields = ('user',)
    readonly_fields = ('updated_at',)

    fieldsets = (
        (None, {'fields': ('user', 'athlete_id', 'scope', 'expires_at', 'updated_at')}),
        (
            'OAuth tokens',
            {
                'classes': ('collapse',),
                'fields': ('access_token', 'refresh_token'),
                'description': 'OAuth tokens are stored for Strava sync.',
            },
        ),
    )
