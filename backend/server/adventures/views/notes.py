from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from adventures.models import CollectionItineraryItem, Note
from adventures.permissions import ensure_can_change_collection
from adventures.serializers import NoteSerializer
from adventures.views.mixins import CollectionOwnedViewSetMixin
from rest_framework import viewsets


class NoteViewSet(CollectionOwnedViewSetMixin, viewsets.ModelViewSet):
    """
    Notes: text with optional links and a date, on their own or in a collection.

    A note in a collection belongs to the collection owner and can be changed by its editors.
    Changing a note's date removes it from the itinerary day it was placed on.
    """

    openapi_tags = ['Trip items']
    model = Note
    queryset = Note.objects.all()
    serializer_class = NoteSerializer

    def perform_update(self, serializer):
        instance = serializer.instance
        ensure_can_change_collection(self.request, instance, serializer.validated_data)

        old_date = instance.date
        new_date = serializer.validated_data.get('date', old_date)

        with transaction.atomic():
            # If the date changed, remove old itinerary items for this note on the old date
            if old_date and new_date and old_date != new_date:
                CollectionItineraryItem.objects.filter(
                    content_type=ContentType.objects.get_for_model(Note),
                    object_id=str(instance.id),
                    date=old_date,
                    day__isnull=True,
                ).delete()
            serializer.save()
