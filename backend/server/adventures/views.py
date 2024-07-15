import requests
from rest_framework.decorators import action
from rest_framework import viewsets
from django.db.models.functions import Lower
from rest_framework.response import Response
from .models import Adventure, Collection
from worldtravel.models import VisitedRegion, Region, Country
from .serializers import AdventureSerializer, CollectionSerializer
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Prefetch
from .permissions import IsOwnerOrReadOnly, IsPublicReadOnly
from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 1000

from rest_framework.pagination import PageNumberPagination

from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

class AdventureViewSet(viewsets.ModelViewSet):
    serializer_class = AdventureSerializer
    permission_classes = [IsOwnerOrReadOnly, IsPublicReadOnly]
    pagination_class = StandardResultsSetPagination

    def apply_sorting(self, queryset):
        order_by = self.request.query_params.get('order_by', 'name')
        order_direction = self.request.query_params.get('order_direction', 'asc')
        include_collections = self.request.query_params.get('include_collections', 'false')

        valid_order_by = ['name', 'type', 'date', 'rating']
        if order_by not in valid_order_by:
            order_by = 'name'

        if order_direction not in ['asc', 'desc']:
            order_direction = 'asc'

        # Apply case-insensitive sorting for the 'name' field
        if order_by == 'name':
            queryset = queryset.annotate(lower_name=Lower('name'))
            ordering = 'lower_name'
        else:
            ordering = order_by

        if order_direction == 'desc':
            ordering = f'-{ordering}'

        print(f"Ordering by: {ordering}")  # For debugging

        if include_collections == 'false':
            queryset = queryset.filter(collection = None)

        return queryset.order_by(ordering)

    def get_queryset(self):
        queryset = Adventure.objects.annotate(
        ).filter(
            Q(is_public=True) | Q(user_id=self.request.user.id)
        )
        return self.apply_sorting(queryset)
    
    def perform_create(self, serializer):
        serializer.save(user_id=self.request.user)

    @action(detail=False, methods=['get'])
    def filtered(self, request):
        types = request.query_params.get('types', '').split(',')
        valid_types = ['visited', 'planned']
        types = [t for t in types if t in valid_types]

        if not types:
            return Response({"error": "No valid types provided"}, status=400)

        queryset = Adventure.objects.none()

        for adventure_type in types:
            if adventure_type in ['visited', 'planned']:
                queryset |= Adventure.objects.filter(
                    type=adventure_type, user_id=request.user.id)

        queryset = self.apply_sorting(queryset)
        adventures = self.paginate_and_respond(queryset, request)
        return adventures
    
    @action(detail=False, methods=['get'])
    def all(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        # include_collections = request.query_params.get('include_collections', 'false')
        # if include_collections not in ['true', 'false']:
        #     include_collections = 'false'

        # if include_collections == 'true':
        #     queryset = Adventure.objects.filter(
        #         Q(is_public=True) | Q(user_id=request.user.id)
        #     )
        # else:
        #     queryset = Adventure.objects.filter(
        #         Q(is_public=True) | Q(user_id=request.user.id), collection=None
        #     )
        queryset = Adventure.objects.filter(
            Q(is_public=True) | Q(user_id=request.user.id)
        )
        
        queryset = self.apply_sorting(queryset)
        serializer = self.get_serializer(queryset, many=True)
       
        return Response(serializer.data)

    def paginate_and_respond(self, queryset, request):
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
class CollectionViewSet(viewsets.ModelViewSet):
    serializer_class = CollectionSerializer
    permission_classes = [IsOwnerOrReadOnly, IsPublicReadOnly]
    pagination_class = StandardResultsSetPagination

    def apply_sorting(self, queryset):
        order_by = self.request.query_params.get('order_by', 'name')
        order_direction = self.request.query_params.get('order_direction', 'asc')

        valid_order_by = ['name']
        if order_by not in valid_order_by:
            order_by = 'name'

        if order_direction not in ['asc', 'desc']:
            order_direction = 'asc'

        # Apply case-insensitive sorting for the 'name' field
        if order_by == 'name':
            queryset = queryset.annotate(lower_name=Lower('name'))
            ordering = 'lower_name'
        else:
            ordering = order_by

        if order_direction == 'desc':
            ordering = f'-{ordering}'

        print(f"Ordering by: {ordering}")  # For debugging

        return queryset.order_by(ordering)

    def get_queryset(self):
        collections =  Collection.objects.filter(
            Q(is_public=True) | Q(user_id=self.request.user.id)
        ).prefetch_related(
            Prefetch('adventure_set', queryset=Adventure.objects.filter(
                Q(is_public=True) | Q(user_id=self.request.user.id)
            ))
        )
        return self.apply_sorting(collections)

    def perform_create(self, serializer):
        serializer.save(user_id=self.request.user)

    # @action(detail=False, methods=['get'])
    # def filtered(self, request):
    #     types = request.query_params.get('types', '').split(',')
    #     valid_types = ['visited', 'planned']
    #     types = [t for t in types if t in valid_types]

    #     if not types:
    #         return Response({"error": "No valid types provided"}, status=400)

    #     queryset = Collection.objects.none()

    #     for adventure_type in types:
    #         if adventure_type in ['visited', 'planned']:
    #             queryset |= Collection.objects.filter(
    #                 type=adventure_type, user_id=request.user.id)

    #     queryset = self.apply_sorting(queryset)
    #     collections = self.paginate_and_respond(queryset, request)
    #     return collections
    
    def paginate_and_respond(self, queryset, request):
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
class StatsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def counts(self, request):
        visited_count = Adventure.objects.filter(
            type='visited', user_id=request.user.id).count()
        planned_count = Adventure.objects.filter(
            type='planned', user_id=request.user.id).count()
        trips_count = Collection.objects.filter(
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
            'trips_count': trips_count,
            'visited_region_count': visited_region_count,
            'total_regions': total_regions,
            'country_count': country_count,
            'total_countries': total_countries
        })
    
class GenerateDescription(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'],)
    def desc(self, request):
        name = self.request.query_params.get('name', '')
        # un url encode the name
        name = name.replace('%20', ' ')
        print(name)
        url = 'https://en.wikipedia.org/w/api.php?origin=*&action=query&prop=extracts&exintro&explaintext&format=json&titles=%s' % name
        response = requests.get(url)
        data = response.json()
        data = response.json()
        page_id = next(iter(data["query"]["pages"]))
        extract = data["query"]["pages"][page_id]
        if extract.get('extract') is None:
            return Response({"error": "No description found"}, status=400)
        return Response(extract)
    @action(detail=False, methods=['get'],)
    def img(self, request):
        name = self.request.query_params.get('name', '')
        # un url encode the name
        name = name.replace('%20', ' ')
        url = 'https://en.wikipedia.org/w/api.php?origin=*&action=query&prop=pageimages&format=json&piprop=original&titles=%s' % name
        response = requests.get(url)
        data = response.json()
        page_id = next(iter(data["query"]["pages"]))
        extract = data["query"]["pages"][page_id]
        if extract.get('original') is None:
            return Response({"error": "No image found"}, status=400)
        return Response(extract["original"])
        