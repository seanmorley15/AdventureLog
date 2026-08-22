from django.contrib import admin
from allauth.account.decorators import secure_admin_login

from main.admin_utils import (
    AdventureLogGeoModelAdmin,
    CoordinatesDisplayMixin,
    UUID_READONLY,
    coordinate_display,
)
from worldtravel.models import City, Country, Region, VisitedCity, VisitedRegion

admin.site.login = secure_admin_login(admin.site.login)


@admin.register(Country)
class CountryAdmin(CoordinatesDisplayMixin, AdventureLogGeoModelAdmin):
    list_display = (
        'name',
        'country_code',
        'subregion',
        'capital',
        'display_coordinates',
        'region_count',
    )
    list_filter = ('subregion',)
    search_fields = ('name', 'country_code', 'capital', 'subregion')
    ordering = ('name',)
    readonly_fields = UUID_READONLY + ('display_coordinates_readonly',)

    fieldsets = (
        (None, {'fields': ('name', 'country_code', 'subregion', 'capital')}),
        (
            'Geography',
            {
                'fields': (
                    'coordinates',
                    'display_coordinates_readonly',
                ),
                'description': 'Set the country centroid on the map (longitude = x, latitude = y).',
            },
        ),
    )

    @admin.display(description='Regions')
    def region_count(self, obj):
        return Region.objects.filter(country=obj).count()

    @admin.display(description='Coordinates (lat, lon)')
    def display_coordinates_readonly(self, obj):
        return coordinate_display(obj.coordinates)


@admin.register(Region)
class RegionAdmin(CoordinatesDisplayMixin, AdventureLogGeoModelAdmin):
    list_display = (
        'name',
        'country',
        'display_coordinates',
        'city_count',
        'visit_count',
    )
    list_filter = ('country', 'country__subregion')
    search_fields = ('name', 'id', 'country__name', 'country__country_code')
    autocomplete_fields = ('country',)
    ordering = ('country__name', 'name')
    readonly_fields = UUID_READONLY + ('display_coordinates_readonly',)

    fieldsets = (
        (None, {'fields': ('id', 'name', 'country')}),
        (
            'Geography',
            {'fields': ('coordinates', 'display_coordinates_readonly')},
        ),
    )

    @admin.display(description='Cities')
    def city_count(self, obj):
        return City.objects.filter(region=obj).count()

    @admin.display(description='Visits')
    def visit_count(self, obj):
        return VisitedRegion.objects.filter(region=obj).count()

    @admin.display(description='Coordinates (lat, lon)')
    def display_coordinates_readonly(self, obj):
        return coordinate_display(obj.coordinates)


@admin.register(City)
class CityAdmin(CoordinatesDisplayMixin, AdventureLogGeoModelAdmin):
    list_display = (
        'name',
        'region',
        'country_name',
        'display_coordinates',
    )
    list_filter = ('region__country', 'region')
    search_fields = ('name', 'id', 'region__name', 'region__country__name')
    autocomplete_fields = ('region',)
    ordering = ('region__country__name', 'region__name', 'name')
    readonly_fields = UUID_READONLY + ('display_coordinates_readonly',)

    fieldsets = (
        (None, {'fields': ('id', 'name', 'region')}),
        (
            'Geography',
            {'fields': ('coordinates', 'display_coordinates_readonly')},
        ),
    )

    @admin.display(description='Country')
    def country_name(self, obj):
        return obj.region.country.name if obj.region_id else '—'

    @admin.display(description='Coordinates (lat, lon)')
    def display_coordinates_readonly(self, obj):
        return coordinate_display(obj.coordinates)


@admin.register(VisitedRegion)
class VisitedRegionAdmin(admin.ModelAdmin):
    list_display = ('user', 'region', 'country_name', 'display_coordinates')
    list_filter = ('region__country', 'user')
    search_fields = (
        'user__username',
        'region__name',
        'region__country__name',
    )
    autocomplete_fields = ('user', 'region')

    @admin.display(description='Country')
    def country_name(self, obj):
        return obj.region.country.name

    @admin.display(description='Region coordinates')
    def display_coordinates(self, obj):
        return coordinate_display(obj.region.coordinates)


@admin.register(VisitedCity)
class VisitedCityAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'region_name', 'country_name', 'display_coordinates')
    list_filter = ('city__region__country', 'user')
    search_fields = (
        'user__username',
        'city__name',
        'city__region__name',
    )
    autocomplete_fields = ('user', 'city')

    @admin.display(description='Region')
    def region_name(self, obj):
        return obj.city.region.name

    @admin.display(description='Country')
    def country_name(self, obj):
        return obj.city.region.country.name

    @admin.display(description='City coordinates')
    def display_coordinates(self, obj):
        return coordinate_display(obj.city.coordinates)
