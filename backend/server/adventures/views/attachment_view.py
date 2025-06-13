from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from adventures.models import Adventure, Attachment
from adventures.serializers import AttachmentSerializer

class AttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Attachment.objects.filter(user_id=self.request.user)

    @action(detail=True, methods=['post'])
    def attachment_delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        adventure_id = request.data.get('adventure')
        try:
            adventure = Adventure.objects.get(id=adventure_id)
        except Adventure.DoesNotExist:
            return Response({"error": "Adventure not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if adventure.user_id != request.user:
            # Check if the adventure has any collections
            if adventure.collections.exists():
                # Check if the user is in the shared_with list of any of the adventure's collections
                user_has_access = False
                for collection in adventure.collections.all():
                    if collection.shared_with.filter(id=request.user.id).exists():
                        user_has_access = True
                        break
                
                if not user_has_access:
                    return Response({"error": "User does not have permission to access this adventure"}, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({"error": "User does not own this adventure"}, status=status.HTTP_403_FORBIDDEN)
        
        return super().create(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        adventure_id = self.request.data.get('adventure')
        adventure = Adventure.objects.get(id=adventure_id)
        
        # If the adventure belongs to collections, set the owner to the collection owner
        if adventure.collections.exists():
            # Get the first collection's owner (assuming all collections have the same owner)
            collection = adventure.collections.first()
            serializer.save(user_id=collection.user_id)
        else:
            # Otherwise, set the owner to the request user
            serializer.save(user_id=self.request.user)