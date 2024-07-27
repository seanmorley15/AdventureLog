# travel/urls.py

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import CountryViewSet, RegionViewSet, VisitedRegionViewSet, regions_by_country, visits_by_country, GeoJSONView

router = DefaultRouter()
router.register(r'countries', CountryViewSet, basename='countries')
router.register(r'regions', RegionViewSet, basename='regions')
router.register(r'visitedregion', VisitedRegionViewSet, basename='visitedregion')

urlpatterns = [
    path('', include(router.urls)),
    path('<str:country_code>/regions/', regions_by_country, name='regions-by-country'),
    path('<str:country_code>/visits/', visits_by_country, name='visits-by-country'),
    path('geojson/', GeoJSONView.as_view({'get': 'list'}), name='geojson'),
]
