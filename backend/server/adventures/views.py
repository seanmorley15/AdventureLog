from rest_framework.decorators import action
from rest_framework import viewsets
from rest_framework.response import Response
from .models import Adventure, Trip
from .serializers import AdventureSerializer, TripSerializer
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .permissions import IsOwnerOrReadOnly

class AdventureViewSet(viewsets.ModelViewSet):
    serializer_class = AdventureSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        return Adventure.objects.filter(
            Q(is_public=True) | Q(user_id=self.request.user.id)
        )

    def perform_create(self, serializer):
        serializer.save(user_id=self.request.user)

    @action(detail=False, methods=['get'])
    def visited(self, request):
        visited_adventures = Adventure.objects.filter(
            type='visited', user_id=request.user.id, trip=None)
        serializer = self.get_serializer(visited_adventures, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def planned(self, request):
        planned_adventures = Adventure.objects.filter(
            type='planned', user_id=request.user.id, trip=None)
        serializer = self.get_serializer(planned_adventures, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        featured_adventures = Adventure.objects.filter(
            type='featured', is_public=True, trip=None)
        serializer = self.get_serializer(featured_adventures, many=True)
        return Response(serializer.data)

class TripViewSet(viewsets.ModelViewSet):
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        return Trip.objects.filter(
            Q(is_public=True) | Q(user_id=self.request.user.id)
        )

    def perform_create(self, serializer):
        serializer.save(user_id=self.request.user)

    @action(detail=False, methods=['get'])
    def visited(self, request):
        trips = Trip.objects.filter(
            type='visited', user_id=request.user.id)
        serializer = self.get_serializer(trips, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def planned(self, request):
        trips = Trip.objects.filter(
            type='planned', user_id=request.user.id)
        serializer = self.get_serializer(trips, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        trips = Trip.objects.filter(
            type='featured', is_public=True)
        serializer = self.get_serializer(trips, many=True)
        return Response(serializer.data)