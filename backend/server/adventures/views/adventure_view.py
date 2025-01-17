from django.db import transaction
from rest_framework.decorators import action
from rest_framework import viewsets
from django.db.models.functions import Lower
from rest_framework.response import Response
from adventures.models import Adventure, Category
from django.core.exceptions import PermissionDenied
from adventures.serializers import AdventureSerializer
from django.db.models import Q
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from django.shortcuts import get_object_or_404
from django.db.models import Max
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
            # order by the earliest visit object associated with the adventure
            queryset = queryset.annotate(latest_visit=Max('visits__start_date'))
            queryset = queryset.filter(latest_visit__isnull=False)
            ordering = 'latest_visit'
        # Apply case-insensitive sorting for the 'name' field
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

        # reverse ordering for updated_at field
        if order_by == 'updated_at':
            if order_direction == 'asc':
                ordering = '-updated_at'
            else:
                ordering = 'updated_at'

        print(f"Ordering by: {ordering}")  # For debugging

        if include_collections == 'false':
            queryset = queryset.filter(collection = None)

        return queryset.order_by(ordering)

    def get_queryset(self):
        print(self.request.user)
        # if the user is not authenticated return only public adventures for retrieve action
        if not self.request.user.is_authenticated:
            if self.action == 'retrieve':
                return Adventure.objects.filter(is_public=True).distinct().order_by('-updated_at')
            return Adventure.objects.none()

        if self.action == 'retrieve':
            # For individual adventure retrieval, include public adventures
            return Adventure.objects.filter(
                Q(is_public=True) | Q(user_id=self.request.user.id) | Q(collection__shared_with=self.request.user)
            ).distinct().order_by('-updated_at')
        else:
            # For other actions, include user's own adventures and shared adventures
            return Adventure.objects.filter(
                Q(user_id=self.request.user.id) | Q(collection__shared_with=self.request.user)
            ).distinct().order_by('-updated_at')

    def retrieve(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        adventure = get_object_or_404(queryset, pk=kwargs['pk'])
        serializer = self.get_serializer(adventure)
        return Response(serializer.data)

    def perform_update(self, serializer):
        adventure = serializer.save()
        if adventure.collection:
            adventure.is_public = adventure.collection.is_public
            adventure.save()
        
    @action(detail=False, methods=['get'])
    def filtered(self, request):
        types = request.query_params.get('types', '').split(',')
        is_visited = request.query_params.get('is_visited', 'all')

        # Handle case where types is all
        if 'all' in types:
            types = Category.objects.filter(user_id=request.user).values_list('name', flat=True)
        
        else:
            for type in types:
                if not Category.objects.filter(user_id=request.user, name=type).exists():
                    return Response({"error": f"Category {type} does not exist"}, status=400)

            if not types:
                return Response({"error": "At least one type must be provided"}, status=400)

        queryset = Adventure.objects.filter(
            category__in=Category.objects.filter(name__in=types, user_id=request.user),
            user_id=request.user.id
        )

        # Handle is_visited filtering
        if is_visited.lower() == 'true':
            serializer = self.get_serializer(queryset, many=True)
            filtered_ids = [
                adventure.id for adventure, serialized_adventure in zip(queryset, serializer.data)
                if serialized_adventure['is_visited']
            ]
            queryset = queryset.filter(id__in=filtered_ids)
        elif is_visited.lower() == 'false':
            serializer = self.get_serializer(queryset, many=True)
            filtered_ids = [
                adventure.id for adventure, serialized_adventure in zip(queryset, serializer.data)
                if not serialized_adventure['is_visited']
            ]
            queryset = queryset.filter(id__in=filtered_ids)
        # If is_visited is 'all' or any other value, we don't apply additional filtering

        # Apply sorting
        queryset = self.apply_sorting(queryset)

        # Paginate and respond
        adventures = self.paginate_and_respond(queryset, request)
        return adventures
        
    @action(detail=False, methods=['get'])
    def all(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        include_collections = request.query_params.get('include_collections', 'false')
        if include_collections not in ['true', 'false']:
            include_collections = 'false'

        if include_collections == 'true':
            queryset = Adventure.objects.filter(
                Q(is_public=True) | Q(user_id=request.user.id)
            )
        else:
            queryset = Adventure.objects.filter(
                Q(is_public=True) | Q(user_id=request.user.id), collection=None
            )
        queryset = Adventure.objects.filter(
            Q(user_id=request.user.id)
        )
        queryset = self.apply_sorting(queryset)
        serializer = self.get_serializer(queryset, many=True)
       
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = self.request.query_params.get('query', '')
        property = self.request.query_params.get('property', 'all')
        if len(query) < 2:
            return Response({"error": "Query must be at least 2 characters long"}, status=400)
        
        if property not in ['name', 'type', 'location', 'description', 'activity_types']:
            property = 'all'

        queryset = Adventure.objects.none()

        if property == 'name':
            queryset = Adventure.objects.filter(
                (Q(name__icontains=query)) &
                (Q(user_id=request.user.id) | Q(is_public=True))
            )
        elif property == 'type':
            queryset = Adventure.objects.filter(
                (Q(type__icontains=query)) &
                (Q(user_id=request.user.id) | Q(is_public=True))
            )
        elif property == 'location':
            queryset = Adventure.objects.filter(
                (Q(location__icontains=query)) &
                (Q(user_id=request.user.id) | Q(is_public=True))
            )
        elif property == 'description':
            queryset = Adventure.objects.filter(
                (Q(description__icontains=query)) &
                (Q(user_id=request.user.id) | Q(is_public=True))
            )
        elif property == 'activity_types':
            queryset = Adventure.objects.filter(
                (Q(activity_types__icontains=query)) &
                (Q(user_id=request.user.id) | Q(is_public=True))
            )
        else:
            queryset = Adventure.objects.filter(
            (Q(name__icontains=query) | Q(description__icontains=query) | Q(location__icontains=query) | Q(activity_types__icontains=query)) &
            (Q(user_id=request.user.id) | Q(is_public=True))
        )
        
        queryset = self.apply_sorting(queryset)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        # Retrieve the current object
        instance = self.get_object()
        
        # Partially update the instance with the request data
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # if the adventure is trying to have is_public changed and its part of a collection return an error
        if new_collection is not None:
            serializer.validated_data['is_public'] = new_collection.is_public
        elif instance.collection:
            serializer.validated_data['is_public'] = instance.collection.is_public


        # Retrieve the collection from the validated data
        new_collection = serializer.validated_data.get('collection')

        user = request.user
        print(new_collection)

        if new_collection is not None and new_collection!=instance.collection:
            # Check if the user is the owner of the new collection
            if new_collection.user_id != user or instance.user_id != user:
                raise PermissionDenied("You do not have permission to use this collection.")
        elif new_collection is None:
            # Handle the case where the user is trying to set the collection to None
            if instance.collection is not None and instance.collection.user_id != user:
                raise PermissionDenied("You cannot remove the collection as you are not the owner.")
        
        # Perform the update
        self.perform_update(serializer)

        # Return the updated instance
        return Response(serializer.data)
    
    def partial_update(self, request, *args, **kwargs):
        # Retrieve the current object
        instance = self.get_object()
        
        # Partially update the instance with the request data
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Retrieve the collection from the validated data
        new_collection = serializer.validated_data.get('collection')

        user = request.user
        print(new_collection)

        # if the adventure is trying to have is_public changed and its part of a collection return an error
        if new_collection is not None:
            serializer.validated_data['is_public'] = new_collection.is_public
        elif instance.collection:
            serializer.validated_data['is_public'] = instance.collection.is_public

        if new_collection is not None and new_collection!=instance.collection:
            # Check if the user is the owner of the new collection
            if new_collection.user_id != user or instance.user_id != user:
                raise PermissionDenied("You do not have permission to use this collection.")
        elif new_collection is None:
            # Handle the case where the user is trying to set the collection to None
            if instance.collection is not None and instance.collection.user_id != user:
                raise PermissionDenied("You cannot remove the collection as you are not the owner.")
        
        # Perform the update
        self.perform_update(serializer)

        # Return the updated instance
        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()
    
    # when creating an adventure, make sure the user is the owner of the collection or shared with the collection
    @transaction.atomic
    def perform_create(self, serializer):
        # Retrieve the collection from the validated data
        collection = serializer.validated_data.get('collection')
        
        # Check if a collection is provided
        if collection:
            user = self.request.user
            # Check if the user is the owner or is in the shared_with list
            if collection.user_id != user and not collection.shared_with.filter(id=user.id).exists():
                # Return an error response if the user does not have permission
                raise PermissionDenied("You do not have permission to use this collection.")
            # if collection the owner of the adventure is the owner of the collection
            # set the is_public field of the adventure to the is_public field of the collection
            serializer.save(user_id=collection.user_id, is_public=collection.is_public)
            return

        # Save the adventure with the current user as the owner
        serializer.save(user_id=self.request.user)

    def paginate_and_respond(self, queryset, request):
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)