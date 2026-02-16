from django.shortcuts import get_object_or_404
from .models import Country, Region, VisitedRegion, City, VisitedCity, ExchangeRate
from .serializers import CitySerializer, CountrySerializer, RegionSerializer, VisitedRegionSerializer, VisitedCitySerializer, ExchangeRateSerializer
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, action
from django.contrib.gis.geos import Point
from adventures.models import Location

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def regions_by_country(request, country_code):
    country = get_object_or_404(Country, country_code=country_code)
    regions = Region.objects.filter(country=country).order_by('name')
    serializer = RegionSerializer(regions, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def visits_by_country(request, country_code):
    country = get_object_or_404(Country, country_code=country_code)
    visits = VisitedRegion.objects.filter(region__country=country, user=request.user.id)
    serializer = VisitedRegionSerializer(visits, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cities_by_region(request, region_id):
    region = get_object_or_404(Region, id=region_id)
    cities = City.objects.filter(region=region).order_by('name')
    serializer = CitySerializer(cities, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def visits_by_region(request, region_id):
    region = get_object_or_404(Region, id=region_id)
    visits = VisitedCity.objects.filter(city__region=region, user=request.user.id)
    serializer = VisitedCitySerializer(visits, many=True)
    return Response(serializer.data)

# view called spin the globe that return a random country, a random region in that country and a random city in that region
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def globespin(request):
    country = Country.objects.order_by('?').first()
    data = {
        "country": CountrySerializer(country).data,
    }
    
    regions = Region.objects.filter(country=country)
    if regions.exists():
        region = regions.order_by('?').first()
        data["region"] = RegionSerializer(region).data
        
        cities = City.objects.filter(region=region)
        if cities.exists():
            city = cities.order_by('?').first()
            data["city"] = CitySerializer(city).data
    
    return Response(data)

class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Country.objects.all().order_by('name')
    serializer_class = CountrySerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def check_point_in_region(self, request):
        lat = float(request.query_params.get('lat'))
        lon = float(request.query_params.get('lon'))
        point = Point(lon, lat, srid=4326)
        region = Region.objects.filter(geometry__contains=point).first()
        if region:
            return Response({'in_region': True, 'region_name': region.name, 'region_id': region.id})
        else:
            return Response({'in_region': False})

    @action(detail=False, methods=['post'])
    def region_check_all_adventures(self, request):
        adventures = Location.objects.filter(user=request.user.id, type='visited')
        count = 0
        for adventure in adventures:
            if adventure.latitude is not None and adventure.longitude is not None:
                try:
                    point = Point(float(adventure.longitude), float(adventure.latitude), srid=4326)
                    region = Region.objects.filter(geometry__contains=point).first()
                    if region:
                        if not VisitedRegion.objects.filter(user=request.user.id, region=region).exists():
                            VisitedRegion.objects.create(user=request.user, region=region)
                            count += 1
                except Exception as e:
                    print(f"Error processing adventure {adventure.id}: {e}")
                    continue
        return Response({'regions_visited': count})

class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    permission_classes = [IsAuthenticated]

class VisitedRegionViewSet(viewsets.ModelViewSet):
    serializer_class = VisitedRegionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return VisitedRegion.objects.filter(user=self.request.user.id)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        request.data['user'] = request.user
        if VisitedRegion.objects.filter(user=request.user.id, region=request.data['region']).exists():
            return Response({"error": "Region already visited by user."}, status=400)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def destroy(self, request, **kwargs):
        region = get_object_or_404(Region, id=kwargs['pk'])
        visited_region = VisitedRegion.objects.filter(user=request.user.id, region=region)
        if visited_region.exists():
            visited_region.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"error": "Visited region not found."}, status=status.HTTP_404_NOT_FOUND)
    
class VisitedCityViewSet(viewsets.ModelViewSet):
    serializer_class = VisitedCitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return VisitedCity.objects.filter(user=self.request.user.id)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        request.data['user'] = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # Ensure a VisitedRegion exists for the city
        region = serializer.validated_data['city'].region
        if not VisitedRegion.objects.filter(user=request.user.id, region=region).exists():
            VisitedRegion.objects.create(user=request.user, region=region)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def destroy(self, request, **kwargs):
        city = get_object_or_404(City, id=kwargs['pk'])
        visited_city = VisitedCity.objects.filter(user=request.user.id, city=city)
        if visited_city.exists():
            visited_city.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"error": "Visited city not found."}, status=status.HTTP_404_NOT_FOUND)


class ExchangeRateViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for exchange rates (base currency: USD)"""
    queryset = ExchangeRate.objects.all().order_by('currency_code')
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def convert(self, request):
        """Convert amount between currencies.

        Query params:
        - amount: Amount to convert (required)
        - from: Source currency code (required)
        - to: Target currency code (required)
        """
        try:
            amount = float(request.query_params.get('amount', 0))
            from_currency = request.query_params.get('from', 'USD').upper()
            to_currency = request.query_params.get('to', 'USD').upper()

            if from_currency == to_currency:
                return Response({
                    'amount': amount,
                    'from': from_currency,
                    'to': to_currency,
                    'converted': amount,
                    'rate': 1.0
                })

            # Get rates (USD is base currency with rate 1.0)
            from_rate = 1.0
            to_rate = 1.0

            if from_currency != 'USD':
                try:
                    from_rate = float(ExchangeRate.objects.get(currency_code=from_currency).rate)
                except ExchangeRate.DoesNotExist:
                    return Response({'error': f'Unknown currency: {from_currency}'}, status=400)

            if to_currency != 'USD':
                try:
                    to_rate = float(ExchangeRate.objects.get(currency_code=to_currency).rate)
                except ExchangeRate.DoesNotExist:
                    return Response({'error': f'Unknown currency: {to_currency}'}, status=400)

            # Convert: amount in FROM -> USD -> TO
            amount_in_usd = amount / from_rate
            converted = amount_in_usd * to_rate
            rate = to_rate / from_rate

            return Response({
                'amount': amount,
                'from': from_currency,
                'to': to_currency,
                'converted': round(converted, 2),
                'rate': round(rate, 6)
            })
        except ValueError:
            return Response({'error': 'Invalid amount'}, status=400)

    @action(detail=False, methods=['get'])
    def all_rates(self, request):
        """Get all exchange rates as a simple dict."""
        rates = {er.currency_code: float(er.rate) for er in ExchangeRate.objects.all()}
        rates['USD'] = 1.0  # Always include USD
        return Response(rates)
