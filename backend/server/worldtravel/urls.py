# travel/urls.py

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import CountryViewSet, RegionViewSet, VisitedRegionViewSet, regions_by_country, visits_by_country, cities_by_region, VisitedCityViewSet, visits_by_region, globespin
router = DefaultRouter()
router.register(r'countries', CountryViewSet, basename='countries')
router.register(r'regions', RegionViewSet, basename='regions')
router.register(r'visitedregion', VisitedRegionViewSet, basename='visitedregion')
router.register(r'visitedcity', VisitedCityViewSet, basename='visitedcity')

urlpatterns = [
    path('', include(router.urls)),
    path('<str:country_code>/regions/', regions_by_country, name='regions-by-country'),
    path('<str:country_code>/visits/', visits_by_country, name='visits-by-country'),
    path('regions/<str:region_id>/cities/', cities_by_region, name='cities-by-region'),
    path('regions/<str:region_id>/cities/visits/', visits_by_region, name='visits-by-region'),
    path('globespin/', globespin, name='globespin'),
]
