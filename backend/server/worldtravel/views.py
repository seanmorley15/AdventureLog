from django.db.models import Count, Q
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view, inline_serializer
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import APIError
from core.pagination import StandardResultsSetPagination
from .models import City, Country, Region, VisitedCity, VisitedRegion
from .serializers import CitySerializer, CountrySerializer, RegionSerializer, VisitedCitySerializer, VisitedRegionSerializer
from .services import mark_regions_visited


def _regions_with_city_counts():
    return Region.objects.select_related('country').annotate(num_cities_annotated=Count('city', distinct=True))


@extend_schema_view(
    list=extend_schema(description='Every country, A to Z, with how many of its regions you have visited.'),
    retrieve=extend_schema(
        parameters=[OpenApiParameter('country_code', str, OpenApiParameter.PATH, description='ISO 3166-1 alpha-2, e.g. `US`.')]
    ),
)
class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    """Countries of the world. Reference data, the same for everyone."""

    openapi_tags = ['World travel']
    openapi_resource_plural = 'countries'
    serializer_class = CountrySerializer
    lookup_field = 'country_code'
    queryset = Country.objects.all()

    def get_queryset(self):
        # Region and visit counts come from the same query instead of two per country.
        return Country.objects.annotate(
            num_regions_annotated=Count('region', distinct=True),
            num_visits_annotated=Count(
                'region__visitedregion',
                filter=Q(region__visitedregion__user=self.request.user.id),
                distinct=True,
            ),
        ).order_by('name')

    @extend_schema(
        parameters=[OpenApiParameter('country_code', str, OpenApiParameter.PATH, description='ISO 3166-1 alpha-2, e.g. `US`.')],
        responses=RegionSerializer(many=True),
    )
    @action(detail=True, methods=['get'])
    def regions(self, request, country_code=None):
        """List a country's regions"""
        country = self.get_object()
        regions = _regions_with_city_counts().filter(country=country).order_by('name')
        return Response(RegionSerializer(regions, many=True, context={'request': request}).data)


@extend_schema_view(
    list=extend_schema(
        parameters=[OpenApiParameter('country', str, description='Only this country (ISO alpha-2 code).')],
    ),
)
class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    """States, provinces and other first-level divisions of a country."""

    openapi_tags = ['World travel']
    serializer_class = RegionSerializer
    pagination_class = StandardResultsSetPagination
    queryset = Region.objects.all()

    def get_queryset(self):
        queryset = _regions_with_city_counts().order_by('name')
        country = self.request.query_params.get('country')
        if self.action == 'list' and country:
            queryset = queryset.filter(country__country_code=country)
        return queryset

    @extend_schema(responses=CitySerializer(many=True))
    @action(detail=True, methods=['get'])
    def cities(self, request, pk=None):
        """List a region's cities"""
        region = self.get_object()
        cities = City.objects.filter(region=region).select_related('region__country').order_by('name')
        return Response(CitySerializer(cities, many=True, context={'request': request}).data)


class _VisitedPlaceViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Shared behaviour of visited regions and visited cities.

    The path id is the region or city itself, not the record, so ``GET``, ``DELETE`` and the
    ``region``/``city`` field all name the same thing.
    """

    openapi_tags = ['World travel']
    model = None
    place_field = None

    def perform_create(self, serializer):
        place = serializer.validated_data[self.place_field]
        if self.model.objects.filter(user=self.request.user, **{self.place_field: place}).exists():
            raise APIError(
                f'You have already visited this {self.place_field}.', code='conflict', status=status.HTTP_409_CONFLICT
            )
        serializer.save(user=self.request.user)


@extend_schema_view(
    list=extend_schema(
        summary='List your visited regions',
        parameters=[OpenApiParameter('country', str, description='Only regions of this country (ISO alpha-2 code).')],
    ),
    create=extend_schema(
        summary='Mark a region visited',
        responses={201: VisitedRegionSerializer, 409: OpenApiResponse(description='Already marked visited.')},
    ),
    retrieve=extend_schema(
        summary='Get a visited region',
        parameters=[OpenApiParameter('region', str, OpenApiParameter.PATH, description='The region id, e.g. `US-CA`.')],
    ),
    destroy=extend_schema(
        summary='Unmark a visited region',
        parameters=[OpenApiParameter('region', str, OpenApiParameter.PATH, description='The region id, e.g. `US-CA`.')],
    ),
)
class VisitedRegionViewSet(_VisitedPlaceViewSet):
    """Regions you have visited. Visiting a location in a region marks it automatically."""

    serializer_class = VisitedRegionSerializer
    model = VisitedRegion
    place_field = 'region'
    lookup_field = 'region'
    queryset = VisitedRegion.objects.all()

    def get_queryset(self):
        queryset = VisitedRegion.objects.filter(user=self.request.user.id).select_related('region__country')
        country = self.request.query_params.get('country')
        if self.action == 'list' and country:
            queryset = queryset.filter(region__country__country_code=country)
        return queryset


@extend_schema_view(
    list=extend_schema(
        summary='List your visited cities',
        parameters=[OpenApiParameter('region', str, description='Only cities of this region (region id).')],
    ),
    create=extend_schema(
        summary='Mark a city visited',
        description='Also marks its region visited.',
        responses={201: VisitedCitySerializer, 409: OpenApiResponse(description='Already marked visited.')},
    ),
    retrieve=extend_schema(
        summary='Get a visited city',
        parameters=[OpenApiParameter('city', str, OpenApiParameter.PATH, description='The city id.')],
    ),
    destroy=extend_schema(
        summary='Unmark a visited city',
        parameters=[OpenApiParameter('city', str, OpenApiParameter.PATH, description='The city id.')],
    ),
)
class VisitedCityViewSet(_VisitedPlaceViewSet):
    """Cities you have visited."""

    serializer_class = VisitedCitySerializer
    model = VisitedCity
    place_field = 'city'
    lookup_field = 'city'
    openapi_resource_plural = 'visited cities'
    queryset = VisitedCity.objects.all()

    def get_queryset(self):
        queryset = VisitedCity.objects.filter(user=self.request.user.id).select_related('city__region__country')
        region = self.request.query_params.get('region')
        if self.action == 'list' and region:
            queryset = queryset.filter(city__region=region)
        return queryset

    def perform_create(self, serializer):
        super().perform_create(serializer)
        mark_regions_visited(self.request.user.id, [serializer.instance.city.region_id])


class GlobeSpinView(APIView):
    openapi_tags = ['World travel']

    @extend_schema(
        responses=inline_serializer('GlobeSpin', fields={
            'country': CountrySerializer(),
            'region': RegionSerializer(required=False, help_text='Absent when the country has no regions.'),
            'city': CitySerializer(required=False, help_text='Absent when the region has no cities.'),
        })
    )
    def get(self, request):
        """
        Spin the globe

        A random country, a random region in it, and a random city in that region.
        """
        country = Country.objects.order_by('?').first()
        if country is None:
            raise APIError('No countries are loaded on this server.', code='not_found', status=status.HTTP_404_NOT_FOUND)
        data = {'country': CountrySerializer(country, context={'request': request}).data}
        region = Region.objects.filter(country=country).select_related('country').order_by('?').first()
        if region is not None:
            data['region'] = RegionSerializer(region).data
            city = City.objects.filter(region=region).order_by('?').first()
            if city is not None:
                data['city'] = CitySerializer(city).data
        return Response(data)
