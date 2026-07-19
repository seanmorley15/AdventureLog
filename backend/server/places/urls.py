from django.urls import path

from .views import NearbyPlacesView

urlpatterns = [
    path('places/nearby/', NearbyPlacesView.as_view(), name='places-nearby'),
]
