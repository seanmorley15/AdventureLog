from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q
from adventures.models import Lodging
from adventures.access.audience import can_edit
from adventures.serializers import LodgingSerializer, add_quick_add_extras
from adventures.views.mixins import CollectionOwnedViewSetMixin
from adventures.utils.query_optimization import media_prefetches
from adventures.throttling import ExternalGeocodeThrottle
from adventures.services.quick_add import QuickAddError, finish_quick_add, prepare_lodging_quick_add

class LodgingViewSet(CollectionOwnedViewSetMixin, viewsets.ModelViewSet):
    model = Lodging
    queryset = Lodging.objects.all()
    serializer_class = LodgingSerializer

    def list(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_403_FORBIDDEN)
        queryset = Lodging.objects.filter(
            Q(user=request.user.id)
        ).select_related('user').prefetch_related(*media_prefetches())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['post'],
        url_path='quick-add',
        throttle_classes=[ExternalGeocodeThrottle],
    )
    def quick_add(self, request):
        """Create a lodging from lightweight map/place input in one server-side call."""
        payload = request.data if isinstance(request.data, dict) else {}

        try:
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
        except QuickAddError as error:
            return Response({"error": error.message}, status=error.status_code)

        response_data = add_quick_add_extras(
            self.get_serializer(lodging).data, itinerary_item, image_import_summary
        )
        return Response(response_data, status=status.HTTP_201_CREATED)
