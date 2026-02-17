from django.contrib import admin
from allauth.account.decorators import secure_admin_login
from .models import Country, Region, City, ExchangeRate, VisitedRegion, VisitedCity

admin.autodiscover()
admin.site.login = secure_admin_login(admin.site.login)


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['name', 'country_code', 'currency_code', 'currency_name', 'capital', 'subregion']
    list_filter = ['subregion', 'currency_code']
    search_fields = ['name', 'country_code', 'currency_code']
    ordering = ['name']


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['name', 'country']
    list_filter = ['country']
    search_fields = ['name', 'country__name']


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'region']
    list_filter = ['region__country']
    search_fields = ['name', 'region__name']


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ['currency_code', 'rate', 'updated_at']
    search_fields = ['currency_code']
    ordering = ['currency_code']


@admin.register(VisitedRegion)
class VisitedRegionAdmin(admin.ModelAdmin):
    list_display = ['user', 'region']
    list_filter = ['region__country']
    search_fields = ['user__username', 'region__name']


@admin.register(VisitedCity)
class VisitedCityAdmin(admin.ModelAdmin):
    list_display = ['user', 'city']
    list_filter = ['city__region__country']
    search_fields = ['user__username', 'city__name']