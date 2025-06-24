from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db.models import Q
from adventures.models import Transportation
from adventures.serializers import TransportationSerializer
from rest_framework.exceptions import PermissionDenied
from adventures.permissions import IsOwnerOrSharedWithFullAccess

class TransportationViewSet(viewsets.ModelViewSet):
    queryset = Transportation.objects.all()
    serializer_class = TransportationSerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess]

    def list(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_403_FORBIDDEN)
        queryset = Transportation.objects.filter(
            Q(user=request.user.id)
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        user = self.request.user
        if self.action == 'retrieve':
            # For individual adventure retrieval, include public locations, user's own locations and shared locations
            return Transportation.objects.filter(
                Q(is_public=True) | Q(user=user.id) | Q(collection__shared_with=user.id)
            ).distinct().order_by('-updated_at')
        # For other actions, include user's own locations and shared locations
        return Transportation.objects.filter(
            Q(user=user.id) | Q(collection__shared_with=user.id)
        ).distinct().order_by('-updated_at')

    def partial_update(self, request, *args, **kwargs):
        # Retrieve the current object
        instance = self.get_object()
        user = request.user

        # Partially update the instance with the request data
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Retrieve the collection from the validated data
        new_collection = serializer.validated_data.get('collection')

        if new_collection is not None and new_collection != instance.collection:
            # Check if the user is the owner of the new collection
            if new_collection.user != user or instance.user != user:
                raise PermissionDenied("You do not have permission to use this collection.")
        elif new_collection is None:
            # Handle the case where the user is trying to set the collection to None
            if instance.collection is not None and instance.collection.user != user:
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
            if collection.user != user and not collection.shared_with.filter(id=user.id).exists():
                # Return an error response if the user does not have permission
                raise PermissionDenied("You do not have permission to use this collection.")
            # if collection the owner of the adventure is the owner of the collection
            serializer.save(user=collection.user)
            return

        # Save the adventure with the current user as the owner
        serializer.save(user=self.request.user)