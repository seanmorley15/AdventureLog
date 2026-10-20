from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db.models import Q
from adventures.models import Checklist, CollectionItineraryItem
from adventures.serializers import ChecklistSerializer
from adventures.permissions import ensure_can_change_collection
from adventures.views.mixins import CollectionOwnedViewSetMixin
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

class ChecklistViewSet(CollectionOwnedViewSetMixin, viewsets.ModelViewSet):
    model = Checklist
    serializer_class = ChecklistSerializer
    filterset_fields = ['is_public', 'collection']

    def list(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_403_FORBIDDEN)
        queryset = Checklist.objects.filter(
            Q(user=request.user)
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_update(self, serializer):
        instance = serializer.instance
        ensure_can_change_collection(self.request, instance, serializer.validated_data)

        old_date = instance.date
        new_date = serializer.validated_data.get('date', old_date)

        with transaction.atomic():
            # If the date changed, remove old itinerary items for this checklist on the old date
            if old_date and new_date and old_date != new_date:
                CollectionItineraryItem.objects.filter(
                    content_type=ContentType.objects.get_for_model(Checklist),
                    object_id=str(instance.id),
                    date=old_date,
                    day__isnull=True,
                ).delete()
            serializer.save()

