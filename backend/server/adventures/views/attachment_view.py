from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from adventures.models import Location, ContentAttachment
from adventures.serializers import AttachmentSerializer

class AttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ContentAttachment.objects.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        location_id = request.data.get('location')
        try:
            location = Location.objects.get(id=location_id)
        except Location.DoesNotExist:
            return Response({"error": "Location not found"}, status=status.HTTP_404_NOT_FOUND)

        if location.user != request.user:
            # Check if the location has any collections
            if location.collections.exists():
                # Check if the user is in the shared_with list of any of the location's collections
                user_has_access = False
                for collection in location.collections.all():
                    if collection.shared_with.filter(id=request.user.id).exists():
                        user_has_access = True
                        break
                
                if not user_has_access:
                    return Response({"error": "User does not have permission to access this location"}, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({"error": "User does not own this location"}, status=status.HTTP_403_FORBIDDEN)
        
        return super().create(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        location_id = self.request.data.get('location')
        location = Location.objects.get(id=location_id)

        # If the location belongs to collections, set the owner to the collection owner
        if location.collections.exists():
            # Get the first collection's owner (assuming all collections have the same owner)
            collection = location.collections.first()
            serializer.save(user=collection.user)
        else:
            # Otherwise, set the owner to the request user
            serializer.save(user=self.request.user)