import uuid
import requests
from django.db import transaction
from rest_framework.decorators import action
from rest_framework import viewsets
from django.db.models.functions import Lower
from rest_framework.response import Response
from .models import Adventure, Checklist, Collection, Transportation, Note, AdventureImage, ADVENTURE_TYPES
from django.core.exceptions import PermissionDenied
from worldtravel.models import VisitedRegion, Region, Country
from .serializers import AdventureImageSerializer, AdventureSerializer, CollectionSerializer, NoteSerializer, TransportationSerializer, ChecklistSerializer
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .permissions import CollectionShared, IsOwnerOrSharedWithFullAccess, IsPublicOrOwnerOrSharedWithFullAccess
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 1000

from rest_framework.pagination import PageNumberPagination

from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

class AdventureViewSet(viewsets.ModelViewSet):
    serializer_class = AdventureSerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess, IsPublicOrOwnerOrSharedWithFullAccess]
    pagination_class = StandardResultsSetPagination

    def apply_sorting(self, queryset):
        order_by = self.request.query_params.get('order_by', 'updated_at')
        order_direction = self.request.query_params.get('order_direction', 'asc')
        include_collections = self.request.query_params.get('include_collections', 'true')

        valid_order_by = ['name', 'type', 'date', 'rating', 'updated_at']
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
        # handle case where types is all
        if 'all' in types:
            types = [t[0] for t in ADVENTURE_TYPES]
        valid_types = [t[0] for t in ADVENTURE_TYPES]
        types = [t for t in types if t in valid_types]

        if not types:
            return Response({"error": "No valid types provided"}, status=400)

        queryset = Adventure.objects.none()

        for adventure_type in types:
            if adventure_type in valid_types:
                queryset |= Adventure.objects.filter(
                    type=adventure_type, user_id=request.user.id)

        queryset = self.apply_sorting(queryset)
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
    
class CollectionViewSet(viewsets.ModelViewSet):
    serializer_class = CollectionSerializer
    permission_classes = [CollectionShared]
    pagination_class = StandardResultsSetPagination

    # def get_queryset(self):
    #     return Collection.objects.filter(Q(user_id=self.request.user.id) & Q(is_archived=False))

    def apply_sorting(self, queryset):
        order_by = self.request.query_params.get('order_by', 'name')
        order_direction = self.request.query_params.get('order_direction', 'asc')

        valid_order_by = ['name', 'upated_at']
        if order_by not in valid_order_by:
            order_by = 'updated_at'

        if order_direction not in ['asc', 'desc']:
            order_direction = 'asc'

        # Apply case-insensitive sorting for the 'name' field
        if order_by == 'name':
            queryset = queryset.annotate(lower_name=Lower('name'))
            ordering = 'lower_name'
            if order_direction == 'desc':
                ordering = f'-{ordering}'
        else:
            order_by == 'updated_at'
            ordering = 'updated_at'
            if order_direction == 'asc':
                ordering = '-updated_at'

        #print(f"Ordering by: {ordering}")  # For debugging

        return queryset.order_by(ordering)
    
    def list(self, request, *args, **kwargs):
        # make sure the user is authenticated
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        queryset = Collection.objects.filter(user_id=request.user.id)
        queryset = self.apply_sorting(queryset)
        collections = self.paginate_and_respond(queryset, request)
        return collections
    
    @action(detail=False, methods=['get'])
    def all(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
       
        queryset = Collection.objects.filter(
            Q(user_id=request.user.id)
        )
        
        queryset = self.apply_sorting(queryset)
        serializer = self.get_serializer(queryset, many=True)
       
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def archived(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
       
        queryset = Collection.objects.filter(
            Q(user_id=request.user.id) & Q(is_archived=True)
        )
        
        queryset = self.apply_sorting(queryset)
        serializer = self.get_serializer(queryset, many=True)
       
        return Response(serializer.data)
    
    # this make the is_public field of the collection cascade to the adventures
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        if 'collection' in serializer.validated_data:
            new_collection = serializer.validated_data['collection']
            # if the new collection is different from the old one and the user making the request is not the owner of the new collection return an error
            if new_collection != instance.collection and new_collection.user_id != request.user:
                return Response({"error": "User does not own the new collection"}, status=400)

        # Check if the 'is_public' field is present in the update data
        if 'is_public' in serializer.validated_data:
            new_public_status = serializer.validated_data['is_public']
            
            # if is_publuc has changed and the user is not the owner of the collection return an error
            if new_public_status != instance.is_public and instance.user_id != request.user:
                print(f"User {request.user.id} does not own the collection {instance.id} that is owned by {instance.user_id}")
                return Response({"error": "User does not own the collection"}, status=400)

            # Update associated adventures to match the collection's is_public status
            Adventure.objects.filter(collection=instance).update(is_public=new_public_status)

            # do the same for transportations
            Transportation.objects.filter(collection=instance).update(is_public=new_public_status)

            # do the same for notes
            Note.objects.filter(collection=instance).update(is_public=new_public_status)

            # Log the action (optional)
            action = "public" if new_public_status else "private"
            print(f"Collection {instance.id} and its adventures were set to {action}")

        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)
    
    # make an action to retreive all adventures that are shared with the user
    @action(detail=False, methods=['get'])
    def shared(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        queryset = Collection.objects.filter(
            shared_with=request.user
        )
        queryset = self.apply_sorting(queryset)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    # Adds a new user to the shared_with field of an adventure
    @action(detail=True, methods=['post'], url_path='share/(?P<uuid>[^/.]+)')
    def share(self, request, pk=None, uuid=None):
        collection = self.get_object()
        if not uuid:
            return Response({"error": "User UUID is required"}, status=400)
        try:
            user = User.objects.get(uuid=uuid, public_profile=True)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        
        if user == request.user:
            return Response({"error": "Cannot share with yourself"}, status=400)
        
        if collection.shared_with.filter(id=user.id).exists():
            return Response({"error": "Adventure is already shared with this user"}, status=400)
        
        collection.shared_with.add(user)
        collection.save()
        return Response({"success": f"Shared with {user.username}"})
    
    @action(detail=True, methods=['post'], url_path='unshare/(?P<uuid>[^/.]+)')
    def unshare(self, request, pk=None, uuid=None):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        collection = self.get_object()
        if not uuid:
            return Response({"error": "User UUID is required"}, status=400)
        try:
            user = User.objects.get(uuid=uuid, public_profile=True)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        
        if user == request.user:
            return Response({"error": "Cannot unshare with yourself"}, status=400)
        
        if not collection.shared_with.filter(id=user.id).exists():
            return Response({"error": "Collection is not shared with this user"}, status=400)
        
        collection.shared_with.remove(user)
        collection.save()
        return Response({"success": f"Unshared with {user.username}"})

    def get_queryset(self):
        if self.action == 'destroy':
            return Collection.objects.filter(user_id=self.request.user.id)
        
        if self.action in ['update', 'partial_update']:
            return Collection.objects.filter(
                Q(user_id=self.request.user.id) | Q(shared_with=self.request.user)
            ).distinct()
        
        if self.action == 'retrieve':
            if not self.request.user.is_authenticated:
                return Collection.objects.filter(is_public=True)
            return Collection.objects.filter(
                Q(is_public=True) | Q(user_id=self.request.user.id) | Q(shared_with=self.request.user)
            ).distinct()
        
        # For list action, include collections owned by the user or shared with the user, that are not archived
        return Collection.objects.filter(
            (Q(user_id=self.request.user.id) | Q(shared_with=self.request.user)) & Q(is_archived=False)
        ).distinct()


    def perform_create(self, serializer):
        # This is ok because you cannot share a collection when creating it
        serializer.save(user_id=self.request.user)
    
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
        adventure_count = Adventure.objects.filter(
            user_id=request.user.id).count()
        trips_count = Collection.objects.filter(
            user_id=request.user.id).count()
        visited_region_count = VisitedRegion.objects.filter(
            user_id=request.user.id).count()
        total_regions = Region.objects.count()
        country_count = VisitedRegion.objects.filter(
            user_id=request.user.id).values('region__country').distinct().count()
        total_countries = Country.objects.count()
        return Response({
            'adventure_count': adventure_count,
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


class ActivityTypesView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def types(self, request):
        """
        Retrieve a list of distinct activity types for adventures associated with the current user.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            Response: A response containing a list of distinct activity types.
        """
        types = Adventure.objects.filter(user_id=request.user.id).values_list('activity_types', flat=True).distinct()

        allTypes = []

        for i in types:
            if not i:
                continue
            for x in i:
                if x and x not in allTypes:
                    allTypes.append(x)

        return Response(allTypes)

class TransportationViewSet(viewsets.ModelViewSet):
    queryset = Transportation.objects.all()
    serializer_class = TransportationSerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess, IsPublicOrOwnerOrSharedWithFullAccess]
    filterset_fields = ['type', 'is_public', 'collection']

    # return error message if user is not authenticated on the root endpoint
    def list(self, request, *args, **kwargs):
        # Prevent listing all adventures
        return Response({"detail": "Listing all transportations is not allowed."},
                        status=status.HTTP_403_FORBIDDEN)
    
    @action(detail=False, methods=['get'])
    def all(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        queryset = Transportation.objects.filter(
            Q(user_id=request.user.id)
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    

    def get_queryset(self):
        # if the user is not authenticated return only public transportations for  retrieve action
        if not self.request.user.is_authenticated:
            if self.action == 'retrieve':
                return Transportation.objects.filter(is_public=True).distinct().order_by('-updated_at')
            return Transportation.objects.none()

        
        if self.action == 'retrieve':
            # For individual adventure retrieval, include public adventures
            return Transportation.objects.filter(
                Q(is_public=True) | Q(user_id=self.request.user.id) | Q(collection__shared_with=self.request.user)
            ).distinct().order_by('-updated_at')
        else:
            # For other actions, include user's own adventures and shared adventures
            return Transportation.objects.filter(
                Q(user_id=self.request.user.id) | Q(collection__shared_with=self.request.user)
            ).distinct().order_by('-updated_at')

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
            serializer.save(user_id=collection.user_id)
            return

        # Save the adventure with the current user as the owner
        serializer.save(user_id=self.request.user)

class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess, IsPublicOrOwnerOrSharedWithFullAccess]
    filterset_fields = ['is_public', 'collection']

    # return error message if user is not authenticated on the root endpoint
    def list(self, request, *args, **kwargs):
        # Prevent listing all adventures
        return Response({"detail": "Listing all notes is not allowed."},
                        status=status.HTTP_403_FORBIDDEN)
    
    @action(detail=False, methods=['get'])
    def all(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        queryset = Note.objects.filter(
            Q(user_id=request.user.id)
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    

    def get_queryset(self):
        # if the user is not authenticated return only public transportations for  retrieve action
        if not self.request.user.is_authenticated:
            if self.action == 'retrieve':
                return Note.objects.filter(is_public=True).distinct().order_by('-updated_at')
            return Note.objects.none()

        
        if self.action == 'retrieve':
            # For individual adventure retrieval, include public adventures
            return Note.objects.filter(
                Q(is_public=True) | Q(user_id=self.request.user.id) | Q(collection__shared_with=self.request.user)
            ).distinct().order_by('-updated_at')
        else:
            # For other actions, include user's own adventures and shared adventures
            return Note.objects.filter(
                Q(user_id=self.request.user.id) | Q(collection__shared_with=self.request.user)
            ).distinct().order_by('-updated_at')

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
            serializer.save(user_id=collection.user_id)
            return

        # Save the adventure with the current user as the owner
        serializer.save(user_id=self.request.user)

class ChecklistViewSet(viewsets.ModelViewSet):
    queryset = Checklist.objects.all()
    serializer_class = ChecklistSerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess, IsPublicOrOwnerOrSharedWithFullAccess]
    filterset_fields = ['is_public', 'collection']

    # return error message if user is not authenticated on the root endpoint
    def list(self, request, *args, **kwargs):
        # Prevent listing all adventures
        return Response({"detail": "Listing all checklists is not allowed."},
                        status=status.HTTP_403_FORBIDDEN)
    
    @action(detail=False, methods=['get'])
    def all(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        queryset = Checklist.objects.filter(
            Q(user_id=request.user.id)
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    

    def get_queryset(self):
        # if the user is not authenticated return only public transportations for  retrieve action
        if not self.request.user.is_authenticated:
            if self.action == 'retrieve':
                return Checklist.objects.filter(is_public=True).distinct().order_by('-updated_at')
            return Checklist.objects.none()

        
        if self.action == 'retrieve':
            # For individual adventure retrieval, include public adventures
            return Checklist.objects.filter(
                Q(is_public=True) | Q(user_id=self.request.user.id) | Q(collection__shared_with=self.request.user)
            ).distinct().order_by('-updated_at')
        else:
            # For other actions, include user's own adventures and shared adventures
            return Checklist.objects.filter(
                Q(user_id=self.request.user.id) | Q(collection__shared_with=self.request.user)
            ).distinct().order_by('-updated_at')

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
            serializer.save(user_id=collection.user_id)
            return

        # Save the adventure with the current user as the owner
        serializer.save(user_id=self.request.user)

class AdventureImageViewSet(viewsets.ModelViewSet):
    serializer_class = AdventureImageSerializer
    permission_classes = [IsAuthenticated]

    def dispatch(self, request, *args, **kwargs):
        print(f"Method: {request.method}")
        return super().dispatch(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def image_delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        adventure_id = request.data.get('adventure')
        try:
            adventure = Adventure.objects.get(id=adventure_id)
        except Adventure.DoesNotExist:
            return Response({"error": "Adventure not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if adventure.user_id != request.user:
            # Check if the adventure has a collection
            if adventure.collection:
                # Check if the user is in the collection's shared_with list
                if not adventure.collection.shared_with.filter(id=request.user.id).exists():
                    return Response({"error": "User does not have permission to access this adventure"}, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({"error": "User does not own this adventure"}, status=status.HTTP_403_FORBIDDEN)
        
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        
        adventure_id = request.data.get('adventure')
        try:
            adventure = Adventure.objects.get(id=adventure_id)
        except Adventure.DoesNotExist:
            return Response({"error": "Adventure not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if adventure.user_id != request.user:
            return Response({"error": "User does not own this adventure"}, status=status.HTTP_403_FORBIDDEN)
        
        return super().update(request, *args, **kwargs)
    
    def perform_destroy(self, instance):
        print("perform_destroy")
        return super().perform_destroy(instance)

    def destroy(self, request, *args, **kwargs):
        print("destroy")
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        
        instance = self.get_object()
        adventure = instance.adventure
        if adventure.user_id != request.user:
            return Response({"error": "User does not own this adventure"}, status=status.HTTP_403_FORBIDDEN)
        
        return super().destroy(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        
        instance = self.get_object()
        adventure = instance.adventure
        if adventure.user_id != request.user:
            return Response({"error": "User does not own this adventure"}, status=status.HTTP_403_FORBIDDEN)
        
        return super().partial_update(request, *args, **kwargs)
    
    @action(detail=False, methods=['GET'], url_path='(?P<adventure_id>[0-9a-f-]+)')
    def adventure_images(self, request, adventure_id=None, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            adventure_uuid = uuid.UUID(adventure_id)
        except ValueError:
            return Response({"error": "Invalid adventure ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        queryset = AdventureImage.objects.filter(
            Q(adventure__id=adventure_uuid) & Q(user_id=request.user)
        )
        
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    def get_queryset(self):
        return AdventureImage.objects.filter(user_id=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user_id=self.request.user)