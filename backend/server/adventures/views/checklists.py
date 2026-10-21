from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from rest_framework import viewsets

from adventures.models import Checklist, CollectionItineraryItem
from adventures.permissions import ensure_can_change_collection
from adventures.serializers import ChecklistSerializer
from adventures.views.mixins import CollectionOwnedViewSetMixin


class ChecklistViewSet(CollectionOwnedViewSetMixin, viewsets.ModelViewSet):
    """
    Checklists with items to tick off, on their own or in a collection.

    Send the full `items` list when creating or updating; items not in it are removed.
    Changing a checklist's date removes it from the itinerary day it was placed on.
    """

    openapi_tags = ['Trip items']
    model = Checklist
    queryset = Checklist.objects.all()
    serializer_class = ChecklistSerializer

    def optimize_list(self, queryset):
        return queryset.prefetch_related('checklistitem_set')

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
