import os
from django.contrib import admin
from django.utils.html import mark_safe
from .models import Location, Checklist, ChecklistItem, Collection, Transportation, Note, ContentImage, Visit, Category, ContentAttachment, Lodging, CollectionInvite, Trail, Activity
from worldtravel.models import Country, Region, VisitedRegion, City, VisitedCity
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


class CountryAdmin(admin.ModelAdmin):
    list_display = ('name', 'country_code', 'number_of_regions')
    list_filter = ('subregion',)
    search_fields = ('name', 'country_code')

    def number_of_regions(self, obj):
        return Region.objects.filter(country=obj).count()

    number_of_regions.short_description = 'Number of Regions'


class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'number_of_visits')
    list_filter = ('country',)
    search_fields = ('name', 'country__name')
    # list_filter = ('country', 'number_of_visits')

    def number_of_visits(self, obj):
        return VisitedRegion.objects.filter(region=obj).count()
    
    number_of_visits.short_description = 'Number of Visits'

class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'country')
    list_filter = ('region', 'region__country')
    search_fields = ('name', 'region__name', 'region__country__name')

    def country(self, obj):
        return obj.region.country.name

    country.short_description = 'Country'

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from users.models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'is_staff', 'is_active', 'image_display', 'measurement_system']
    readonly_fields = ('uuid',)
    search_fields = ('username',)
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('profile_pic', 'uuid', 'public_profile', 'disable_password', 'measurement_system')}),
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
    list_display = ('location', 'start_date', 'end_date', 'notes')
    list_filter = ('start_date', 'end_date')
    search_fields = ('notes',)


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

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(Collection, CollectionAdmin)
admin.site.register(Visit, VisitAdmin)
admin.site.register(Country, CountryAdmin)
admin.site.register(Region, RegionAdmin)
admin.site.register(VisitedRegion)
admin.site.register(Transportation)
admin.site.register(Note)
admin.site.register(Checklist)
admin.site.register(ChecklistItem)
admin.site.register(ContentImage, ContentImageImageAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(City, CityAdmin)
admin.site.register(VisitedCity)
admin.site.register(ContentAttachment)
admin.site.register(Lodging)
admin.site.register(CollectionInvite, CollectionInviteAdmin)
admin.site.register(Trail)
admin.site.register(Activity, ActivityAdmin)

admin.site.site_header = 'AdventureLog Admin'
admin.site.site_title = 'AdventureLog Admin Site'
admin.site.index_title = 'Welcome to AdventureLog Admin Page'
