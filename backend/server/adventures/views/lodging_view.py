from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q
from adventures.models import Lodging
from adventures.serializers import LodgingSerializer
from rest_framework.exceptions import PermissionDenied
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from adventures.geocoding import reverse_geocode
from .location_image_view import import_remote_images_for_object
from .quick_add_utils import (
    build_quick_add_description,
    coerce_bool,
    coerce_coordinate,
    coerce_float,
    extract_google_place_details,
    infer_lodging_type,
    preferred_link,
    resolve_quick_add_collection,
    sanitize_photo_urls,
)

class LodgingViewSet(viewsets.ModelViewSet):
    queryset = Lodging.objects.all()
    serializer_class = LodgingSerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess]

    def list(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_403_FORBIDDEN)
        queryset = Lodging.objects.filter(
            Q(user=request.user.id)
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        user = self.request.user
        if self.action == 'retrieve':
            # For individual adventure retrieval, include public locations, user's own locations and shared locations
            return Lodging.objects.filter(
                Q(is_public=True) | Q(user=user.id) | Q(collection__shared_with=user.id)
            ).distinct().order_by('-updated_at')
        # For other actions, include user's own locations and shared locations
        return Lodging.objects.filter(
            Q(user=user.id) | Q(collection__shared_with=user.id)
        ).distinct().order_by('-updated_at')

    def partial_update(self, request, *args, **kwargs):
        # Retrieve the current object
        instance = self.get_object()
        user = request.user

        # Partially update the instance with the request data
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Retrieve the collection from the validated data
        new_collection = serializer.validated_data.get('collection')

        if new_collection is not None and new_collection != instance.collection:
            # Check if the user is the owner of the new collection
            if new_collection.user != user or instance.user != user:
                raise PermissionDenied("You do not have permission to use this collection.")
        elif new_collection is None:
            # Handle the case where the user is trying to set the collection to None
            if instance.collection is not None and instance.collection.user != user:
                raise PermissionDenied("You cannot remove the collection as you are not the owner.")
        
        # Perform the update
        self.perform_update(serializer)
        
        # Return the updated instance
        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()

    @action(detail=False, methods=['post'], url_path='quick-add')
    @transaction.atomic
    def quick_add(self, request):
        """Create a lodging from lightweight map/place input in one server-side call."""
        payload = request.data if isinstance(request.data, dict) else {}

        name = str(payload.get('name') or '').strip()
        if not name:
            return Response({"error": "name is required"}, status=status.HTTP_400_BAD_REQUEST)

        latitude = coerce_coordinate(payload.get('latitude'), -90, 90)
        longitude = coerce_coordinate(payload.get('longitude'), -180, 180)
        if latitude is None or longitude is None:
            return Response(
                {"error": "Valid latitude and longitude are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        collection = resolve_quick_add_collection(
            payload.get('collection_id'),
            validate_permissions=self._validate_collection_permissions,
            permission_error_message=(
                "You do not have permission to add this lodging to the selected collection."
            ),
        )
        if isinstance(collection, Response):
            return collection

        reverse_data = {}
        try:
            reverse_result = reverse_geocode(latitude, longitude, request.user)
            if isinstance(reverse_result, dict) and 'error' not in reverse_result:
                reverse_data = reverse_result
        except Exception:
            reverse_data = {}

        _, details = extract_google_place_details(payload, fallback_query=name)

        rating = coerce_float(payload.get('rating'))
        if rating is None:
            rating = coerce_float(details.get('rating'))

        location_label = (
            str(payload.get('location') or '').strip()
            or str(reverse_data.get('display_name') or '').strip()
            or str(details.get('formatted_address') or '').strip()
            or None
        )

        place_types = payload.get('types')
        if not isinstance(place_types, list) or not place_types:
            place_types = details.get('types') if isinstance(details.get('types'), list) else []

        serializer_payload = {
            'name': name,
            'type': infer_lodging_type(payload.get('type'), place_types),
            'location': location_label,
            'latitude': latitude,
            'longitude': longitude,
            'rating': rating,
            'description': build_quick_add_description(
                base_description=payload.get('description'),
                detailed_description=details.get('description'),
            ),
            'link': preferred_link(payload, details),
            'is_public': coerce_bool(payload.get('is_public'), default=False),
        }

        if collection:
            serializer_payload['collection'] = str(collection.id)

        serializer = self.get_serializer(data=serializer_payload)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        lodging = serializer.instance

        photo_urls = sanitize_photo_urls(payload.get('photos'))
        image_import_summary = None
        if photo_urls:
            image_import_summary = import_remote_images_for_object(
                lodging,
                photo_urls,
                owner=lodging.user,
                max_workers=min(5, len(photo_urls)),
            )

        response_data = self.get_serializer(lodging).data
        if image_import_summary and image_import_summary.get('failed'):
            response_data['quick_add_image_import'] = {
                'created_count': image_import_summary['created_count'],
                'failed_count': image_import_summary['failed_count'],
                'failed': image_import_summary['failed'],
            }

        return Response(response_data, status=status.HTTP_201_CREATED)
    
    # when creating an adventure, make sure the user is the owner of the collection or shared with the collection
    def perform_create(self, serializer):
        # Retrieve the collection from the validated data
        collection = serializer.validated_data.get('collection')

        # Check if a collection is provided
        if collection:
            user = self.request.user
            # Check if the user is the owner or is in the shared_with list
            if collection.user != user and not collection.shared_with.filter(id=user.id).exists():
                # Return an error response if the user does not have permission
                raise PermissionDenied("You do not have permission to use this collection.")
            # if collection the owner of the adventure is the owner of the collection
            serializer.save(user=collection.user)
            return

        # Save the adventure with the current user as the owner
        serializer.save(user=self.request.user)

    def _validate_collection_permissions(self, collections):
        """Validate permissions for all collections (used by quick add)."""
        for collection in collections:
            if collection.user != self.request.user:
                if not collection.shared_with.filter(id=self.request.user.id).exists():
                    raise PermissionDenied(
                        f"You don't have permission to add lodging to collection '{collection.name}'"
                    )