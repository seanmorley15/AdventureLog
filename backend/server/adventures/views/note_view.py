from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db.models import Q
from adventures.models import Note, CollectionItineraryItem
from adventures.serializers import NoteSerializer
from rest_framework.exceptions import PermissionDenied
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from adventures.utils.audience import can_edit, member_collections_q
from rest_framework.decorators import action
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess]
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
    

    def get_queryset(self):
        user = self.request.user
        # Owned rows and rows in collections the requester is a member of or holds a
        # guest link to. A row's own is_public opens it only when no collection owns it.
        scope = member_collections_q(self.request, 'collection__')
        if user.is_authenticated:
            scope |= Q(user=user.id)
        if self.action == 'retrieve':
            scope |= Q(is_public=True, collection__isnull=True)
        return Note.objects.filter(scope).distinct().order_by('-updated_at')

    def partial_update(self, request, *args, **kwargs):
        # Retrieve the current object
        instance = self.get_object()
        
        # Store the old date before updating
        old_date = instance.date
        
        # Partially update the instance with the request data
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Retrieve the collection from the validated data
        new_collection = serializer.validated_data.get('collection')
        new_date = serializer.validated_data.get('date', old_date)

        user = request.user

        if new_collection is not None and new_collection!=instance.collection:
            # Check if the user is the owner of the new collection
            if new_collection.user != user or instance.user != user:
                raise PermissionDenied("You do not have permission to use this collection.")
        elif new_collection is None:
            # Handle the case where the user is trying to set the collection to None
            if instance.collection is not None and instance.collection.user != user:
                raise PermissionDenied("You cannot remove the collection as you are not the owner.")
        
        # If the date changed, remove old itinerary items for this note on the old date
        if old_date and new_date and old_date != new_date:
            note_ct = ContentType.objects.get_for_model(Note)
            old_itinerary_items = CollectionItineraryItem.objects.filter(
                content_type=note_ct,
                object_id=str(instance.id),
                date=old_date,
                day__isnull=True,
            )
            old_itinerary_items.delete()
        
        # Perform the update
        self.perform_update(serializer)

        # Return the updated instance
        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()
    
    # when creating an adventure, make sure the user is the owner of the collection or shared with the collection
    def perform_create(self, serializer):
        # Retrieve the collection from the validated data
        collection = serializer.validated_data.get('collection')

        # Check if a collection is provided
        if collection:
            # Owner, editor, or guest editor. Viewers cannot add records.
            if not can_edit(self.request, collection):
                # Return an error response if the user does not have permission
                raise PermissionDenied("You do not have permission to use this collection.")
            # if collection the owner of the adventure is the owner of the collection
            serializer.save(user=collection.user)
            return

        # Save the adventure with the current user as the owner
        if not self.request.user.is_authenticated:
            raise PermissionDenied("A guest link can only add records to its collection.")
        serializer.save(user=self.request.user)
