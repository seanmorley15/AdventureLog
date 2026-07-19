from django.urls import path

from .views import NearbyPlacesView, SuggestPlacesView

urlpatterns = [
    path('places/nearby/', NearbyPlacesView.as_view(), name='places-nearby'),
    path('places/suggest/', SuggestPlacesView.as_view(), name='places-suggest'),
]
