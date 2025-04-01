from django.utils import timezone
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Max
from django.db.models.functions import Lower
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from adventures.models import Adventure, Category, Transportation, Lodging
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from adventures.serializers import AdventureSerializer, TransportationSerializer, LodgingSerializer
from adventures.utils import pagination

class AdventureViewSet(viewsets.ModelViewSet):
    serializer_class = AdventureSerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess]
    pagination_class = pagination.StandardResultsSetPagination

    def apply_sorting(self, queryset):
        order_by = self.request.query_params.get('order_by', 'updated_at')
        order_direction = self.request.query_params.get('order_direction', 'asc')
        include_collections = self.request.query_params.get('include_collections', 'true')

        valid_order_by = ['name', 'type', 'date', 'rating', 'updated_at']
        if order_by not in valid_order_by:
            order_by = 'name'

        if order_direction not in ['asc', 'desc']:
            order_direction = 'asc'

        if order_by == 'date':
            queryset = queryset.annotate(latest_visit=Max('visits__start_date')).filter(latest_visit__isnull=False)
            ordering = 'latest_visit'
        elif order_by == 'name':
            queryset = queryset.annotate(lower_name=Lower('name'))
            ordering = 'lower_name'
        elif order_by == 'rating':
            queryset = queryset.filter(rating__isnull=False)
            ordering = 'rating'
        else:
            ordering = order_by

        if order_direction == 'desc':
            ordering = f'-{ordering}'

        if order_by == 'updated_at':
            ordering = '-updated_at' if order_direction == 'asc' else 'updated_at'

        if include_collections == 'false':
            queryset = queryset.filter(collection=None)

        return queryset.order_by(ordering)

    def get_queryset(self):
        """
        Returns the queryset for the AdventureViewSet. Unauthenticated users can only
        retrieve public adventures, while authenticated users can access their own,
        shared, and public adventures depending on the action.
        """
        user = self.request.user

        if not user.is_authenticated:
            # Unauthenticated users can only access public adventures for retrieval
            if self.action == 'retrieve':
                return Adventure.objects.retrieve_adventures(user, include_public=True).order_by('-updated_at')
            return Adventure.objects.none()

        # Authenticated users: Handle retrieval separately
        include_public = self.action == 'retrieve'
        return Adventure.objects.retrieve_adventures(
            user,
            include_public=include_public,
            include_owned=True,
            include_shared=True
        ).order_by('-updated_at')

    def perform_update(self, serializer):
        adventure = serializer.save()
        if adventure.collection:
            adventure.is_public = adventure.collection.is_public
            adventure.save()

    @action(detail=False, methods=['get'])
    def filtered(self, request):
        types = request.query_params.get('types', '').split(',')
        is_visited = request.query_params.get('is_visited', 'all')

        if 'all' in types:
            types = Category.objects.filter(user_id=request.user).values_list('name', flat=True)
        else:
            if not types or not all(
                Category.objects.filter(user_id=request.user, name=type).exists() for type in types
            ):
                return Response({"error": "Invalid category or no types provided"}, status=400)

        queryset = Adventure.objects.filter(
            category__in=Category.objects.filter(name__in=types, user_id=request.user),
            user_id=request.user.id
        )

        is_visited_param = request.query_params.get('is_visited')
        if is_visited_param is not None:
            # Convert is_visited_param to a boolean
            if is_visited_param.lower() == 'true':
                is_visited_bool = True
            elif is_visited_param.lower() == 'false':
                is_visited_bool = False
            else:
                is_visited_bool = None

            # Filter logic: "visited" means at least one visit with start_date <= today
            now = timezone.now().date()
            if is_visited_bool is True:
                queryset = queryset.filter(visits__start_date__lte=now).distinct()
            elif is_visited_bool is False:
                queryset = queryset.exclude(visits__start_date__lte=now).distinct()

        queryset = self.apply_sorting(queryset)
        return self.paginate_and_respond(queryset, request)

    @action(detail=False, methods=['get'])
    def all(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)

        include_collections = request.query_params.get('include_collections', 'false') == 'true'
        queryset = Adventure.objects.filter(
            Q(is_public=True) | Q(user_id=request.user.id),
            collection=None if not include_collections else Q()
        )

        queryset = self.apply_sorting(queryset)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        new_collection = serializer.validated_data.get('collection')
        if new_collection and new_collection!=instance.collection:
            if new_collection.user_id != request.user or instance.user_id != request.user:
                raise PermissionDenied("You do not have permission to use this collection.")
        elif new_collection is None and instance.collection and instance.collection.user_id != request.user:
            raise PermissionDenied("You cannot remove the collection as you are not the owner.")

        self.perform_update(serializer)
        return Response(serializer.data)

    @transaction.atomic
    def perform_create(self, serializer):
        collection = serializer.validated_data.get('collection')

        if collection and not (collection.user_id == self.request.user or collection.shared_with.filter(id=self.request.user.id).exists()):
            raise PermissionDenied("You do not have permission to use this collection.")
        elif collection:
            serializer.save(user_id=collection.user_id, is_public=collection.is_public)
            return

        serializer.save(user_id=self.request.user, is_public=collection.is_public if collection else False)

    def paginate_and_respond(self, queryset, request):
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    # @action(detail=True, methods=['post'])
    # def convert(self, request, pk=None):
    #     """
    #     Convert an Adventure instance into a Transportation or Lodging instance.
    #     Expects a JSON body with "target_type": "transportation" or "lodging".
    #     """
    #     adventure = self.get_object()
    #     target_type = request.data.get("target_type", "").lower()

    #     if target_type not in ["transportation", "lodging"]:
    #         return Response(
    #             {"error": "Invalid target type. Must be 'transportation' or 'lodging'."},
    #             status=400
    #         )
    #     if not adventure.collection:
    #         return Response(
    #             {"error": "Adventure must be part of a collection to be converted."},
    #             status=400
    #         )

    #     # Define the overlapping fields that both the Adventure and target models share.
    #     overlapping_fields = ["name", "description",  "is_public", 'collection']

    #     # Gather the overlapping data from the adventure instance.
    #     conversion_data = {}
    #     for field in overlapping_fields:
    #         if hasattr(adventure, field):
    #             conversion_data[field] = getattr(adventure, field)

    #     # Make sure to include the user reference
    #     conversion_data["user_id"] = adventure.user_id

    #     # Convert the adventure instance within an atomic transaction.
    #     with transaction.atomic():
    #         if target_type == "transportation":
    #             new_instance = Transportation.objects.create(**conversion_data)
    #             serializer = TransportationSerializer(new_instance)
    #         else:  # target_type == "lodging"
    #             new_instance = Lodging.objects.create(**conversion_data)
    #             serializer = LodgingSerializer(new_instance)

    #         # Optionally, delete the original adventure to avoid duplicates.
    #         adventure.delete()

    #     return Response(serializer.data)
