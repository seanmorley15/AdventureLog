"""
Mixins for shared view behavior across Transportation and Lodging viewsets.

Provides: CollaborativeQuerySetMixin, EntityCRUDMixin, SunTimesMixin, TypeFilteredMixin

Used by: TransportationViewSet, LodgingViewSet
"""

from django.db.models import Q
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
import requests


class CollaborativeQuerySetMixin:
    """
    Mixin providing get_queryset() and list() for entity viewsets
    that support collaborative mode.

    Uses self.queryset.model to derive the model class dynamically.
    """

    def get_queryset(self):
        user = self.request.user
        is_collaborative = getattr(settings, 'COLLABORATIVE_MODE', False)
        model = self.queryset.model

        if self.action == 'retrieve':
            return model.objects.filter(
                Q(is_public=True) | Q(user=user.id) | Q(collections__shared_with=user.id)
            ).distinct().order_by('-updated_at')

        if is_collaborative and self.action != 'destroy':
            return model.objects.filter(
                Q(is_public=True) | Q(user=user.id) | Q(collections__shared_with=user.id)
            ).distinct().order_by('-updated_at')

        return model.objects.filter(
            Q(user=user.id) | Q(collections__shared_with=user.id)
        ).distinct().order_by('-updated_at')

    def list(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_403_FORBIDDEN)

        is_collaborative = getattr(settings, 'COLLABORATIVE_MODE', False)
        model = self.queryset.model

        if is_collaborative:
            queryset = model.objects.filter(
                Q(user=request.user.id) | Q(is_public=True) | Q(collections__shared_with=request.user.id)
            ).distinct()
        else:
            queryset = model.objects.filter(
                Q(user=request.user.id) | Q(collections__shared_with=request.user.id)
            ).distinct()

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class EntityCRUDMixin:
    """
    Mixin providing partial_update, perform_create, and perform_update
    for entity viewsets.

    Used by: TransportationViewSet, LodgingViewSet
    (Location has different logic for collection permissions.)
    """

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        new_collections = serializer.validated_data.get('collections')

        if new_collections is not None:
            for collection in new_collections:
                if collection.user != user:
                    raise PermissionDenied("You do not have permission to use this collection.")

        self.perform_update(serializer)
        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()

    def perform_create(self, serializer):
        collections = serializer.validated_data.get('collections', [])
        user = self.request.user

        if collections:
            for collection in collections:
                if collection.user != user and not collection.shared_with.filter(id=user.id).exists():
                    raise PermissionDenied("You do not have permission to use this collection.")

        serializer.save(user=user)


class SunTimesMixin:
    """
    Mixin providing additional_info() and _get_sun_times() for entity viewsets.

    Subclasses should set:
        lat_field: attribute name for latitude (default: 'latitude')
        lng_field: attribute name for longitude (default: 'longitude')
    """
    lat_field = 'latitude'
    lng_field = 'longitude'

    @action(detail=True, methods=['get'], url_path='additional-info')
    def additional_info(self, request, pk=None):
        """Get entity with additional sunrise/sunset information."""
        instance = self.get_object()

        serializer = self.get_serializer(instance)
        response_data = serializer.data

        response_data['sun_times'] = self._get_sun_times(instance, response_data.get('visits', []))
        return Response(response_data)

    def _get_sun_times(self, instance, visits):
        """Get sunrise/sunset times for entity visits."""
        sun_times = []
        lat = getattr(instance, self.lat_field, None)
        lng = getattr(instance, self.lng_field, None)

        for visit in visits:
            date = visit.get('start_date')
            if not (date and lng and lat):
                continue

            api_url = (
                f'https://api.sunrisesunset.io/json?'
                f'lat={lat}&lng={lng}&date={date}'
            )

            try:
                response = requests.get(api_url)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', {})

                    if results.get('sunrise') and results.get('sunset'):
                        sun_times.append({
                            "date": date,
                            "visit_id": visit.get('id'),
                            "sunrise": results.get('sunrise'),
                            "sunset": results.get('sunset')
                        })
            except requests.RequestException:
                continue

        return sun_times


class TypeFilteredMixin:
    """
    Mixin providing filtered() action for entity viewsets with type-based filtering.

    Subclasses should set:
        type_choices: list of (key, label) tuples for valid types
        entity_type_label: label used in error messages (e.g., "transportation", "lodging")
    """
    type_choices = []
    entity_type_label = 'entity'

    @action(detail=False, methods=['get'])
    def filtered(self, request):
        """Filter entities by type, visit status, and visibility."""
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_403_FORBIDDEN)

        types_param = request.query_params.get('types', '')
        types = types_param.split(',') if types_param else []
        is_collaborative = getattr(settings, 'COLLABORATIVE_MODE', False)

        valid_types = [t[0] for t in self.type_choices]
        model = self.queryset.model

        if is_collaborative:
            base_filter = Q(user=request.user) | Q(is_public=True) | Q(collections__shared_with=request.user)
        else:
            base_filter = Q(user=request.user) | Q(collections__shared_with=request.user)

        if 'all' in types or not types:
            queryset = model.objects.filter(base_filter).distinct()
        else:
            filtered_types = [t for t in types if t in valid_types]
            if not filtered_types:
                return Response(
                    {"error": f"Invalid {self.entity_type_label} type provided"},
                    status=400
                )
            queryset = model.objects.filter(
                base_filter,
                type__in=filtered_types
            ).distinct()

        queryset = self._apply_visit_filtering(queryset, request)
        queryset = self._apply_public_filtering(queryset, request)
        queryset = self._apply_ownership_filtering(queryset, request)
        queryset = self._apply_rating_filtering(queryset, request)

        queryset = self.apply_sorting(queryset)
        return self.paginate_and_respond(queryset, request)
