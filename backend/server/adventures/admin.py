import os
from django.contrib import admin
from django.utils.html import mark_safe, format_html
from django.urls import reverse
from .models import Location, Checklist, ChecklistItem, Collection, Transportation, Note, ContentImage, Visit, Category, ContentAttachment, Lodging, CollectionInvite, Trail, Activity, CollectionItineraryItem, CollectionItineraryDay, TransportationType, LodgingType, AdventureType, ActivityType
# worldtravel models are now registered in worldtravel/admin.py
from allauth.account.decorators import secure_admin_login

admin.autodiscover()
admin.site.login = secure_admin_login(admin.site.login)

@admin.action(description="Trigger geocoding")
def trigger_geocoding(modeladmin, request, queryset):
    count = 0
    for location in queryset:
        try:
            location.save()  # Triggers geocoding logic in your model
            count += 1
        except Exception as e:
            modeladmin.message_user(request, f"Error geocoding {location}: {e}", level='error')
    modeladmin.message_user(request, f"Geocoding triggered for {count} locations.", level='success')
    


class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_category', 'get_visit_count',  'user', 'is_public')
    list_filter = ( 'user', 'is_public')
    search_fields = ('name',)
    readonly_fields = ('city', 'region', 'country')
    actions = [trigger_geocoding]

    def get_category(self, obj):
        if obj.category and obj.category.display_name and obj.category.icon:
            return obj.category.display_name + ' ' + obj.category.icon
        elif obj.category and obj.category.name:
            return obj.category.name
        else:
            return 'No Category'
        
    get_category.short_description = 'Category'

    def get_visit_count(self, obj):
        return obj.visits.count()
    
    get_visit_count.short_description = 'Visit Count'


from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from users.models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'is_staff', 'is_active', 'image_display', 'measurement_system', 'default_currency']
    readonly_fields = ('uuid',)
    search_fields = ('username',)
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('profile_pic', 'uuid', 'public_profile', 'disable_password', 'measurement_system', 'default_currency')}),
    )
    def image_display(self, obj):
        if obj.profile_pic:
            public_url = os.environ.get('PUBLIC_URL', 'http://127.0.0.1:8000').rstrip('/')
            public_url = public_url.replace("'", "")
            return mark_safe(f'<img src="{public_url}/media/{obj.profile_pic.name}" width="100px" height="100px"')
        else:
            return
        
class ContentImageImageAdmin(admin.ModelAdmin):
    list_display = ('user', 'image_display')

    def image_display(self, obj):
        if obj.image:
            public_url = os.environ.get('PUBLIC_URL', 'http://127.0.0.1:8000').rstrip('/')
            public_url = public_url.replace("'", "")
            return mark_safe(f'<img src="{public_url}/media/{obj.image.name}" width="100px" height="100px"')
        else:
            return


class VisitAdmin(admin.ModelAdmin):
    list_display = ('get_parent', 'get_parent_type', 'start_date', 'end_date', 'user', 'notes')
    list_filter = ('start_date', 'end_date')
    search_fields = ('notes', 'location__name', 'transportation__name', 'lodging__name')

    def get_parent(self, obj):
        if obj.location:
            return obj.location.name
        elif obj.transportation:
            return obj.transportation.name
        elif obj.lodging:
            return obj.lodging.name
        return 'Unknown'
    get_parent.short_description = 'Parent'

    def get_parent_type(self, obj):
        if obj.location:
            return 'Location'
        elif obj.transportation:
            return 'Transportation'
        elif obj.lodging:
            return 'Lodging'
        return 'Unknown'
    get_parent_type.short_description = 'Type'


    def image_display(self, obj):
        if obj.image:  # Ensure this field matches your model's image field
            public_url = os.environ.get('PUBLIC_URL', 'http://127.0.0.1:8000').rstrip('/')
            public_url = public_url.replace("'", "")
            return mark_safe(f'<img src="{public_url}/media/{obj.image.name}" width="100px" height="100px"')
        else:
            return

    image_display.short_description = 'Image Preview'

class CollectionInviteAdmin(admin.ModelAdmin):
    list_display = ('collection', 'invited_user', 'created_at')
    search_fields = ('collection__name', 'invited_user__username')
    readonly_fields = ('created_at',)

    def invited_user(self, obj):
        return obj.invited_user.username if obj.invited_user else 'N/A'
    
    invited_user.short_description = 'Invited User'

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'display_name', 'icon')
    search_fields = ('name', 'display_name')
        
class CollectionAdmin(admin.ModelAdmin):
   

    list_display = ('name', 'user', 'is_public')

class ActivityAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'visit__location', 'sport_type', 'distance', 'elevation_gain', 'moving_time')

class CollectionItineraryItemAdmin(admin.ModelAdmin):
    list_display = ('collection', 'content_type', 'object_link', 'date', 'order')
    search_fields = ('collection__name', 'content_type__model')
    list_filter = ('content_type', 'date')
    raw_id_fields = ('collection',)
    readonly_fields = ('created_at',)

    def object_link(self, obj):
        """
        Display the generic related object; link to its admin change page if registered.
        """
        linked_obj = obj.item
        if not linked_obj:
            return "—"
        try:
            ct = obj.content_type
            app_label = ct.app_label
            model = ct.model
            admin_url = reverse('admin:%s_%s_change' % (app_label, model), args=[obj.object_id])
            return format_html('<a href="{}">{}</a>', admin_url, str(linked_obj))
        except Exception:
            # Fallback to plain text if any error (object not registered, missing id, etc.)
            return str(linked_obj)

    object_link.short_description = 'Item'

class TransportationTypeAdmin(admin.ModelAdmin):
    list_display = ('key', 'name', 'icon', 'display_order', 'is_active')
    list_editable = ('name', 'icon', 'display_order', 'is_active')
    search_fields = ('key', 'name')
    ordering = ('display_order', 'name')


class LodgingTypeAdmin(admin.ModelAdmin):
    list_display = ('key', 'name', 'icon', 'display_order', 'is_active')
    list_editable = ('name', 'icon', 'display_order', 'is_active')
    search_fields = ('key', 'name')
    ordering = ('display_order', 'name')


class AdventureTypeAdmin(admin.ModelAdmin):
    list_display = ('key', 'name', 'icon', 'display_order', 'is_active')
    list_editable = ('name', 'icon', 'display_order', 'is_active')
    search_fields = ('key', 'name')
    ordering = ('display_order', 'name')


class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ('key', 'name', 'icon', 'color', 'display_order', 'is_active')
    list_editable = ('name', 'icon', 'color', 'display_order', 'is_active')
    search_fields = ('key', 'name')
    ordering = ('display_order', 'name')


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(Collection, CollectionAdmin)
admin.site.register(Visit, VisitAdmin)
admin.site.register(Transportation)
admin.site.register(Note)
admin.site.register(Checklist)
admin.site.register(ChecklistItem)
admin.site.register(ContentImage, ContentImageImageAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(ContentAttachment)
admin.site.register(Lodging)
admin.site.register(CollectionInvite, CollectionInviteAdmin)
admin.site.register(Trail)
admin.site.register(Activity, ActivityAdmin)
admin.site.register(CollectionItineraryItem, CollectionItineraryItemAdmin)
admin.site.register(CollectionItineraryDay)
admin.site.register(TransportationType, TransportationTypeAdmin)
admin.site.register(LodgingType, LodgingTypeAdmin)
admin.site.register(AdventureType, AdventureTypeAdmin)
admin.site.register(ActivityType, ActivityTypeAdmin)

admin.site.site_header = 'AdventureLog Admin'
admin.site.site_title = 'AdventureLog Admin Site'
admin.site.index_title = 'Welcome to AdventureLog Admin Page'
