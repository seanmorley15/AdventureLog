from django.contrib import admin
from .models import BucketItem


@admin.register(BucketItem)
class BucketItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'status', 'is_public', 'created_at')
    list_filter = ('status', 'is_public')
    search_fields = ('title', 'description')
