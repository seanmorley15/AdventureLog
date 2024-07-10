from rest_framework.decorators import action
from rest_framework import viewsets
from rest_framework.response import Response
from .models import Adventure, Trip
from worldtravel.models import VisitedRegion, Region, Country
from .serializers import AdventureSerializer, TripSerializer
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Prefetch
from .permissions import IsOwnerOrReadOnly, IsPublicReadOnly

class AdventureViewSet(viewsets.ModelViewSet):
    serializer_class = AdventureSerializer
    permission_classes = [IsOwnerOrReadOnly, IsPublicReadOnly]

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
    permission_classes = [IsOwnerOrReadOnly, IsPublicReadOnly]

    def get_queryset(self):
        return Trip.objects.filter(
            Q(is_public=True) | Q(user_id=self.request.user.id)
        ).prefetch_related(
            Prefetch('adventure_set', queryset=Adventure.objects.filter(
                Q(is_public=True) | Q(user_id=self.request.user.id)
            ))
        )

    def perform_create(self, serializer):
        serializer.save(user_id=self.request.user)

    @action(detail=False, methods=['get'])
    def visited(self, request):
        trips = self.get_queryset().filter(type='visited', user_id=request.user.id)
        serializer = self.get_serializer(trips, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def planned(self, request):
        trips = self.get_queryset().filter(type='planned', user_id=request.user.id)
        serializer = self.get_serializer(trips, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        trips = self.get_queryset().filter(type='featured', is_public=True)
        serializer = self.get_serializer(trips, many=True)
        return Response(serializer.data)
    
class StatsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def counts(self, request):
        visited_count = Adventure.objects.filter(
            type='visited', user_id=request.user.id).count()
        planned_count = Adventure.objects.filter(
            type='planned', user_id=request.user.id).count()
        featured_count = Adventure.objects.filter(
            type='featured', is_public=True).count()
        trips_count = Trip.objects.filter(
            user_id=request.user.id).count()
        visited_region_count = VisitedRegion.objects.filter(
            user_id=request.user.id).count()
        total_regions = Region.objects.count()
        country_count = VisitedRegion.objects.filter(
            user_id=request.user.id).values('region__country').distinct().count()
        total_countries = Country.objects.count()
        return Response({
            'visited_count': visited_count,
            'planned_count': planned_count,
            'featured_count': featured_count,
            'trips_count': trips_count,
            'visited_region_count': visited_region_count,
            'total_regions': total_regions,
            'country_count': country_count,
            'total_countries': total_countries
        })