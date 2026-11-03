from rest_framework import viewsets

from adventures.models import Transportation
from adventures.serializers import TransportationSerializer
from adventures.utils.query_optimization import media_prefetches
from adventures.views.mixins import CollectionOwnedViewSetMixin


class TransportationViewSet(CollectionOwnedViewSetMixin, viewsets.ModelViewSet):
    """
    Flights, trains, drives and other journeys, on their own or in a collection.

    Times are stored in UTC with the time zone of each end (`start_timezone`, `end_timezone`).
    A journey in a collection belongs to the collection owner and can be changed by its editors.
    """

    openapi_tags = ['Trip items']
    openapi_resource = 'transportation'
    model = Transportation
    queryset = Transportation.objects.all()
    serializer_class = TransportationSerializer

    def optimize_list(self, queryset):
        return queryset.select_related('user').prefetch_related(*media_prefetches())
