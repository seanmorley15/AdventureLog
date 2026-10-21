"""Looking places up with the map providers: search, details, reverse geocoding, descriptions, images."""

import logging

import requests
from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from adventures.serializers.places import (
    DescriptionQuerySerializer,
    DescriptionSerializer,
    ImageLookupQuerySerializer,
    ImageLookupSerializer,
    PlaceDetailsQuerySerializer,
    PlaceDetailsSerializer,
    PlaceSearchQuerySerializer,
    PlaceSearchResponseSerializer,
    ReverseGeocodeQuerySerializer,
    ReverseGeocodeSerializer,
)
from adventures.services.descriptions.google import fetch_google_description
from adventures.services.descriptions.wikipedia import WikipediaDescriptionService
from adventures.services.geocoding.reverse import reverse_geocode
from adventures.services.places.details import get_place_details
from adventures.services.places.search import search_places
from adventures.throttling import ExternalGeocodeThrottle, ExternalWikipediaThrottle
from core.exceptions import APIError
from core.serializers import validated

logger = logging.getLogger(__name__)

_UPSTREAM = OpenApiResponse(description='The provider failed (`upstream_error`).')
_NOT_FOUND = OpenApiResponse(description='Nothing was found (`not_found`).')


class PlacesViewSet(viewsets.ViewSet):
    """
    Lookups against the map and encyclopedia providers.

    Google is used when the server has a Google Maps API key, with OpenStreetMap as the
    fallback; descriptions and pictures come from Wikipedia unless Google is asked for.
    Results are cached on the server.
    """

    openapi_tags = ['Places']
    throttle_classes = [ExternalGeocodeThrottle]

    @extend_schema(parameters=[PlaceSearchQuerySerializer], responses=PlaceSearchResponseSerializer)
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search for places

        Finds places by name or address, or what is at a `lat,lon` point. When every provider
        fails the answer is still 200, with no results and a `warning`.
        """
        query = validated(PlaceSearchQuerySerializer, request.query_params)['q'].strip()
        selection = search_places(query)
        body = {
            'count': 0 if selection.error else len(selection.results),
            'results': [] if selection.error else selection.results,
            'provider_used': selection.provider_used,
            'providers_attempted': selection.providers_attempted,
        }
        if selection.error:
            body['warning'] = selection.error
        return Response(body)

    @extend_schema(
        parameters=[PlaceDetailsQuerySerializer],
        responses={200: PlaceDetailsSerializer, 502: _UPSTREAM},
    )
    @action(detail=False, methods=['get'])
    def details(self, request):
        """
        Get a place's details

        Address, contact details, rating and a short description for a `place_id` from a search.
        """
        params = validated(PlaceDetailsQuerySerializer, request.query_params)
        details = get_place_details(params['place_id'].strip(), fallback_query=params['name'], language=params['lang'])
        if isinstance(details, dict) and details.get('error') and not details.get('description'):
            raise APIError(details['error'], code='upstream_error', status=status.HTTP_502_BAD_GATEWAY)
        return Response(details)

    @extend_schema(
        parameters=[ReverseGeocodeQuerySerializer],
        responses={200: ReverseGeocodeSerializer, 502: _UPSTREAM},
    )
    @action(detail=False, methods=['get'])
    def reverse(self, request):
        """
        Reverse geocode a point

        The country, region and city at a point, matched to AdventureLog's world data, and
        whether you have visited them.
        """
        params = validated(ReverseGeocodeQuerySerializer, request.query_params)
        selection = reverse_geocode(params['lat'], params['lon'], request.user)
        data = selection.data
        if isinstance(data, dict) and data.get('error'):
            raise APIError(
                'No place could be found for these coordinates.', code='upstream_error',
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(data)

    @extend_schema(
        parameters=[DescriptionQuerySerializer],
        responses={200: DescriptionSerializer, 404: _NOT_FOUND, 502: _UPSTREAM,
                   503: OpenApiResponse(description='`source=google` but Google Maps is not set up (`not_configured`).')},
    )
    @action(detail=False, methods=['get'], url_path='description', throttle_classes=[ExternalWikipediaThrottle])
    def describe(self, request):
        """
        Get a description

        A short plain-text description of a place or topic from Wikipedia, or from Google's
        place summary and reviews with `source=google`.
        """
        params = validated(DescriptionQuerySerializer, request.query_params)
        name = params['name'].strip()
        try:
            if params['source'] == 'google':
                if not (getattr(settings, 'GOOGLE_MAPS_API_KEY', '') or '').strip():
                    raise RuntimeError('google_maps_disabled')
                page = fetch_google_description(name, place_id=params.get('place_id') or None)
            else:
                service = WikipediaDescriptionService()
                page = service.get_description(name, service.get_language(params.get('lang')))
        except RuntimeError:
            raise APIError('Google Maps is not configured on this server.', code='not_configured', status=503)
        except (requests.exceptions.RequestException, ValueError):
            logger.exception('Failed to fetch a description for %s', name)
            raise APIError('The description service could not be reached.', code='upstream_error', status=502)
        if not page:
            raise APIError('No description found.', code='not_found', status=status.HTTP_404_NOT_FOUND)
        return Response(page)

    @extend_schema(
        parameters=[ImageLookupQuerySerializer],
        responses={200: ImageLookupSerializer, 404: _NOT_FOUND, 502: _UPSTREAM},
    )
    @action(detail=False, methods=['get'], throttle_classes=[ExternalWikipediaThrottle])
    def images(self, request):
        """
        Find pictures

        Up to eight pictures of a place or topic from Wikipedia, for importing into a record
        with `POST /api/images/import-from-urls/`.
        """
        params = validated(ImageLookupQuerySerializer, request.query_params)
        service = WikipediaDescriptionService()
        try:
            images = service.get_images(params['name'].strip(), service.get_language(params.get('lang')))
        except (requests.exceptions.RequestException, ValueError):
            logger.exception('Failed to fetch Wikipedia images')
            raise APIError('Wikipedia could not be reached.', code='upstream_error', status=502)
        if not images:
            raise APIError('No pictures found.', code='not_found', status=status.HTTP_404_NOT_FOUND)
        return Response({'images': images})
