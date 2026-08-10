from django.contrib import admin
from allauth.account.decorators import secure_admin_login

from achievements.models import Achievement, UserAchievement
from main.admin_utils import admin_image_preview

admin.site.login = secure_admin_login(admin.site.login)


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'key', 'type', 'icon_preview', 'earned_count')
    list_filter = ('type',)
    search_fields = ('name', 'key', 'description')
    readonly_fields = ('icon_preview_large',)
    ordering = ('name',)

    fieldsets = (
        (None, {'fields': ('name', 'key', 'type', 'description')}),
        ('Rules', {'fields': ('condition',)}),
        ('Art', {'fields': ('icon', 'icon_preview_large')}),
    )

    @admin.display(description='Icon')
    def icon_preview(self, obj):
        return admin_image_preview(obj.icon, 32, 32)

    @admin.display(description='Icon preview')
    def icon_preview_large(self, obj):
        return admin_image_preview(obj.icon, 96, 96)

    @admin.display(description='Users earned')
    def earned_count(self, obj):
        return UserAchievement.objects.filter(achievement=obj).count()


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'earned_at')
    list_filter = ('achievement', 'earned_at')
    search_fields = ('user__username', 'achievement__name', 'achievement__key')
    autocomplete_fields = ('user', 'achievement')
    date_hierarchy = 'earned_at'
    readonly_fields = ('earned_at',)
