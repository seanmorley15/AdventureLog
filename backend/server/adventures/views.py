from rest_framework.decorators import action
from rest_framework import viewsets
from rest_framework.response import Response
from .models import Adventure
from .serializers import AdventureSerializer
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

# Create your views here.

class AdventureViewSet(viewsets.ModelViewSet):
    serializer_class = AdventureSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Allow any user to see public adventures or their own adventures
        return Adventure.objects.filter(
            Q(is_public=True) | Q(user_id=self.request.user.id)
        )

    def perform_create(self, serializer):
        serializer.save(user_id=self.request.user)

    # Custom actions to return visited and planned adventures
    @action(detail=False, methods=['get'])
    def visited(self, request):
        visited_adventures = Adventure.objects.filter(
            type='visited', user_id=request.user.id, trip_id=None)
        serializer = self.get_serializer(visited_adventures, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def planned(self, request):
        planned_adventures = Adventure.objects.filter(
            type='planned', user_id=request.user.id, trip_id=None)
        serializer = self.get_serializer(planned_adventures, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        featured_adventures = Adventure.objects.filter(
            type='featured', is_public=True, trip_id=None)
        serializer = self.get_serializer(featured_adventures, many=True)
        return Response(serializer.data)