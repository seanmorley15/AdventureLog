from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db.models import Q
from adventures.models import Note, CollectionItineraryItem
from adventures.serializers import NoteSerializer
from adventures.permissions import ensure_can_change_collection
from adventures.views.mixins import CollectionOwnedViewSetMixin
from rest_framework.decorators import action
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

class NoteViewSet(CollectionOwnedViewSetMixin, viewsets.ModelViewSet):
    model = Note
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    filterset_fields = ['is_public', 'collection']

    # return error message if user is not authenticated on the root endpoint
    def list(self, request, *args, **kwargs):
        # Prevent listing all locations
        return Response({"detail": "Listing all notes is not allowed."},
                        status=status.HTTP_403_FORBIDDEN)
    
    @action(detail=False, methods=['get'])
    def all(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        queryset = Note.objects.filter(
            Q(user=request.user.id)
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    

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

