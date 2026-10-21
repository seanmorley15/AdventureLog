from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from adventures.models import Lodging
from adventures.access.audience import can_edit
from adventures.serializers import LodgingSerializer, add_quick_add_extras
from adventures.serializers.quick_add import LodgingQuickAddResultSerializer, QuickAddSerializer
from adventures.views.mixins import CollectionOwnedViewSetMixin
from adventures.utils.query_optimization import media_prefetches
from adventures.throttling import ExternalGeocodeThrottle
from adventures.services.quick_add import finish_quick_add, prepare_lodging_quick_add

class LodgingViewSet(CollectionOwnedViewSetMixin, viewsets.ModelViewSet):
    """
    Places to stay, on their own or in a collection.

    Check-in and check-out are stored in UTC with the stay's `timezone`. A stay in a collection
    belongs to the collection owner and can be changed by its editors.
    """

    openapi_tags = ['Trip items']
    openapi_resource = 'lodging'
    openapi_resource_plural = 'lodgings'
    model = Lodging
    queryset = Lodging.objects.all()
    serializer_class = LodgingSerializer

    def optimize_list(self, queryset):
        return queryset.select_related('user').prefetch_related(*media_prefetches())

    @extend_schema(request=QuickAddSerializer, responses={201: LodgingQuickAddResultSerializer})
    @action(
        detail=False,
        methods=['post'],
        url_path='quick-add',
        throttle_classes=[ExternalGeocodeThrottle],
    )
    def quick_add(self, request):
        """
        Add a stay from a map pin

        Creates a lodging from a place picked on the map or from search, in one call: looks up
        the address, optionally adds it to a collection and its itinerary, and imports up to a
        few photos. Everything is undone if any step fails.
        """
        payload = request.data if isinstance(request.data, dict) else {}

        # Anything that fails inside rolls the whole thing back, so a refusal leaves no half-made lodging.
        with transaction.atomic():
            prepared = prepare_lodging_quick_add(
                request.user, payload, can_add_to_collection=lambda collection: can_edit(request, collection)
            )
            serializer = self.get_serializer(data=prepared.serializer_payload)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

            lodging = serializer.instance
            itinerary_item, image_import_summary = finish_quick_add(lodging, prepared, payload)

        response_data = add_quick_add_extras(
            self.get_serializer(lodging).data, itinerary_item, image_import_summary
        )
        return Response(response_data, status=status.HTTP_201_CREATED)
