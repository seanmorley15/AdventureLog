"""World travel routes. Mounted at ``api/`` by ``main.api_urls``."""

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import CountryViewSet, GlobeSpinView, RegionViewSet, VisitedCityViewSet, VisitedRegionViewSet

router = SimpleRouter()
router.register(r'countries', CountryViewSet, basename='countries')
router.register(r'regions', RegionViewSet, basename='regions')
router.register(r'visited-regions', VisitedRegionViewSet, basename='visited-regions')
router.register(r'visited-cities', VisitedCityViewSet, basename='visited-cities')

urlpatterns = [
    path('globe-spin/', GlobeSpinView.as_view(), name='globe-spin'),
    path('', include(router.urls)),
]
