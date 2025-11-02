from django.contrib import admin
from .models import BucketItem


@admin.register(BucketItem)
class BucketItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'description')
