from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db.models import Q
from adventures.models import Note
from adventures.serializers import NoteSerializer
from rest_framework.exceptions import PermissionDenied
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from rest_framework.decorators import action

class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess]
    filterset_fields = ['is_public', 'collection']

    # return error message if user is not authenticated on the root endpoint
    def list(self, request, *args, **kwargs):
        # Prevent listing all adventures
        return Response({"detail": "Listing all notes is not allowed."},
                        status=status.HTTP_403_FORBIDDEN)
    
    @action(detail=False, methods=['get'])
    def all(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        queryset = Note.objects.filter(
            Q(user_id=request.user.id)
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    

    def get_queryset(self):
        # if the user is not authenticated return only public transportations for  retrieve action
        if not self.request.user.is_authenticated:
            if self.action == 'retrieve':
                return Note.objects.filter(is_public=True).distinct().order_by('-updated_at')
            return Note.objects.none()

        
        if self.action == 'retrieve':
            # For individual adventure retrieval, include public adventures
            return Note.objects.filter(
                Q(is_public=True) | Q(user_id=self.request.user.id) | Q(collection__shared_with=self.request.user)
            ).distinct().order_by('-updated_at')
        else:
            # For other actions, include user's own adventures and shared adventures
            return Note.objects.filter(
                Q(user_id=self.request.user.id) | Q(collection__shared_with=self.request.user)
            ).distinct().order_by('-updated_at')

    def partial_update(self, request, *args, **kwargs):
        # Retrieve the current object
        instance = self.get_object()
        
        # Partially update the instance with the request data
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Retrieve the collection from the validated data
        new_collection = serializer.validated_data.get('collection')

        user = request.user
        print(new_collection)

        if new_collection is not None and new_collection!=instance.collection:
            # Check if the user is the owner of the new collection
            if new_collection.user_id != user or instance.user_id != user:
                raise PermissionDenied("You do not have permission to use this collection.")
        elif new_collection is None:
            # Handle the case where the user is trying to set the collection to None
            if instance.collection is not None and instance.collection.user_id != user:
                raise PermissionDenied("You cannot remove the collection as you are not the owner.")
        
        # Perform the update
        self.perform_update(serializer)

        # Return the updated instance
        return Response(serializer.data)
    
    def partial_update(self, request, *args, **kwargs):
        # Retrieve the current object
        instance = self.get_object()
        
        # Partially update the instance with the request data
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Retrieve the collection from the validated data
        new_collection = serializer.validated_data.get('collection')

        user = request.user
        print(new_collection)

        if new_collection is not None and new_collection!=instance.collection:
            # Check if the user is the owner of the new collection
            if new_collection.user_id != user or instance.user_id != user:
                raise PermissionDenied("You do not have permission to use this collection.")
        elif new_collection is None:
            # Handle the case where the user is trying to set the collection to None
            if instance.collection is not None and instance.collection.user_id != user:
                raise PermissionDenied("You cannot remove the collection as you are not the owner.")
        
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
            user = self.request.user
            # Check if the user is the owner or is in the shared_with list
            if collection.user_id != user and not collection.shared_with.filter(id=user.id).exists():
                # Return an error response if the user does not have permission
                raise PermissionDenied("You do not have permission to use this collection.")
            # if collection the owner of the adventure is the owner of the collection
            serializer.save(user_id=collection.user_id)
            return

        # Save the adventure with the current user as the owner
        serializer.save(user_id=self.request.user)
