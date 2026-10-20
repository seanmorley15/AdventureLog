from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db.models import Q
from adventures.models import Transportation
from adventures.serializers import TransportationSerializer
from adventures.views.mixins import CollectionOwnedViewSetMixin
from adventures.utils.query_optimization import media_prefetches

class TransportationViewSet(CollectionOwnedViewSetMixin, viewsets.ModelViewSet):
    model = Transportation
    queryset = Transportation.objects.all()
    serializer_class = TransportationSerializer

    def list(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_403_FORBIDDEN)
        queryset = Transportation.objects.filter(
            Q(user=request.user.id)
        ).select_related('user').prefetch_related(*media_prefetches())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

