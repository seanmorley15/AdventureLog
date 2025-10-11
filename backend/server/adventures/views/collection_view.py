from django.db.models import Q, Prefetch
from django.db.models.functions import Lower
from django.db import transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from adventures.models import Collection, Location, Transportation, Note, Checklist, CollectionInvite, ContentImage
from adventures.permissions import CollectionShared
from adventures.serializers import CollectionSerializer, CollectionInviteSerializer, UltraSlimCollectionSerializer
from users.models import CustomUser as User
from adventures.utils import pagination
from users.serializers import CustomUserDetailsSerializer as UserSerializer


class CollectionViewSet(viewsets.ModelViewSet):
    serializer_class = CollectionSerializer
    permission_classes = [CollectionShared]
    pagination_class = pagination.StandardResultsSetPagination

    def get_serializer_class(self):
        """Return different serializers based on the action"""
        if self.action in ['list', 'all', 'archived', 'shared']:
            return UltraSlimCollectionSerializer
        return CollectionSerializer

    def apply_sorting(self, queryset):
        order_by = self.request.query_params.get('order_by', 'name')
        order_direction = self.request.query_params.get('order_direction', 'asc')

        valid_order_by = ['name', 'updated_at', 'start_date']
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
        elif order_by == 'start_date':
            ordering = 'start_date'
            if order_direction == 'asc':
                ordering = 'start_date'
            else:
                ordering = '-start_date'
        else:
            order_by == 'updated_at'
            ordering = 'updated_at'
            if order_direction == 'asc':
                ordering = '-updated_at'

        return queryset.order_by(ordering)
    
    def get_serializer_context(self):
        """Override to add nested and exclusion contexts based on query parameters"""
        context = super().get_serializer_context()
        
        # Handle nested parameter (only for full serializer actions)
        if self.action not in ['list', 'all', 'archived', 'shared']:
            is_nested = self.request.query_params.get('nested', 'false').lower() == 'true'
            if is_nested:
                context['nested'] = True
            
            # Handle individual exclusion parameters (if using granular approach)
            exclude_params = [
                'exclude_transportations',
                'exclude_notes', 
                'exclude_checklists',
                'exclude_lodging'
            ]
            
            for param in exclude_params:
                if self.request.query_params.get(param, 'false').lower() == 'true':
                    context[param] = True
                    
        return context

    def get_optimized_queryset_for_listing(self):
        """Get optimized queryset for list actions with prefetching"""
        return self.get_base_queryset().select_related('user').prefetch_related(
            Prefetch(
                'locations__images',
                queryset=ContentImage.objects.filter(is_primary=True).select_related('user'),
                to_attr='primary_images'
            )
        )

    def get_base_queryset(self):
        """Base queryset logic extracted for reuse"""
        if self.action == 'destroy':
            return Collection.objects.filter(user=self.request.user.id)
        
        if self.action in ['update', 'partial_update']:
            return Collection.objects.filter(
                Q(user=self.request.user.id) | Q(shared_with=self.request.user)
            ).distinct()
        
        # Allow access to collections with pending invites for accept/decline actions
        if self.action in ['accept_invite', 'decline_invite']:
            if not self.request.user.is_authenticated:
                return Collection.objects.none()
            return Collection.objects.filter(
                Q(user=self.request.user.id) | 
                Q(shared_with=self.request.user) | 
                Q(invites__invited_user=self.request.user)
            ).distinct()
        
        if self.action == 'retrieve':
            if not self.request.user.is_authenticated:
                return Collection.objects.filter(is_public=True)
            return Collection.objects.filter(
                Q(is_public=True) | Q(user=self.request.user.id) | Q(shared_with=self.request.user)
            ).distinct()
        
        # For list action, include collections owned by the user or shared with the user, that are not archived
        return Collection.objects.filter(
            (Q(user=self.request.user.id) | Q(shared_with=self.request.user)) & Q(is_archived=False)
        ).distinct()

    def get_queryset(self):
        """Get queryset with optimizations for list actions"""
        if self.action in ['list', 'all', 'archived', 'shared']:
            return self.get_optimized_queryset_for_listing()
        return self.get_base_queryset()
    
    def list(self, request):
        # make sure the user is authenticated
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        
        queryset = Collection.objects.filter(
            (Q(user=request.user.id) | Q(shared_with=request.user)) & Q(is_archived=False)
        ).distinct().select_related('user').prefetch_related(
            Prefetch(
                'locations__images',
                queryset=ContentImage.objects.filter(is_primary=True).select_related('user'),
                to_attr='primary_images'
            )
        )
        
        queryset = self.apply_sorting(queryset)
        return self.paginate_and_respond(queryset, request)
    
    @action(detail=False, methods=['get'])
    def all(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
       
        queryset = Collection.objects.filter(
            Q(user=request.user)
        ).select_related('user').prefetch_related(
            Prefetch(
                'locations__images',
                queryset=ContentImage.objects.filter(is_primary=True).select_related('user'),
                to_attr='primary_images'
            )
        )
        
        queryset = self.apply_sorting(queryset)
        serializer = self.get_serializer(queryset, many=True)
       
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def archived(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
       
        queryset = Collection.objects.filter(
            Q(user=request.user.id) & Q(is_archived=True)
        ).select_related('user').prefetch_related(
            Prefetch(
                'locations__images',
                queryset=ContentImage.objects.filter(is_primary=True).select_related('user'),
                to_attr='primary_images'
            )
        )
        
        queryset = self.apply_sorting(queryset)
        serializer = self.get_serializer(queryset, many=True)
       
        return Response(serializer.data)
    
    # this make the is_public field of the collection cascade to the locations
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        if 'collection' in serializer.validated_data:
            new_collection = serializer.validated_data['collection']
            # if the new collection is different from the old one and the user making the request is not the owner of the new collection return an error
            if new_collection != instance.collection and new_collection.user != request.user:
                return Response({"error": "User does not own the new collection"}, status=400)

        # Check if the 'is_public' field is present in the update data
        if 'is_public' in serializer.validated_data:
            new_public_status = serializer.validated_data['is_public']
            
            # if is_public has changed and the user is not the owner of the collection return an error
            if new_public_status != instance.is_public and instance.user != request.user:
                print(f"User {request.user.id} does not own the collection {instance.id} that is owned by {instance.user}")
                return Response({"error": "User does not own the collection"}, status=400)

            # Get all locations in this collection
            locations_in_collection = Location.objects.filter(collections=instance)
            
            if new_public_status:
                # If collection becomes public, make all locations public
                locations_in_collection.update(is_public=True)
            else:
                # If collection becomes private, check each location
                # Only set a location to private if ALL of its collections are private
                # Collect locations that do NOT belong to any other public collection (excluding the current one)
                location_ids_to_set_private = []

                for location in locations_in_collection:
                    has_public_collection = location.collections.filter(is_public=True).exclude(id=instance.id).exists()
                    if not has_public_collection:
                        location_ids_to_set_private.append(location.id)

                # Bulk update those locations
                Location.objects.filter(id__in=location_ids_to_set_private).update(is_public=False)

            # Update transportations, notes, and checklists related to this collection
            # These still use direct ForeignKey relationships
            Transportation.objects.filter(collection=instance).update(is_public=new_public_status)
            Note.objects.filter(collection=instance).update(is_public=new_public_status)
            Checklist.objects.filter(collection=instance).update(is_public=new_public_status)

            # Log the action (optional)
            action = "public" if new_public_status else "private"
            print(f"Collection {instance.id} and its related objects were set to {action}")

        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)
    
    # make an action to retreive all locations that are shared with the user
    @action(detail=False, methods=['get'])
    def shared(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        
        queryset = Collection.objects.filter(
            shared_with=request.user
        ).select_related('user').prefetch_related(
            Prefetch(
                'locations__images',
                queryset=ContentImage.objects.filter(is_primary=True).select_related('user'),
                to_attr='primary_images'
            )
        )
        
        queryset = self.apply_sorting(queryset)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    # Created a custom action to share a collection with another user by their UUID
    # This action will create a CollectionInvite instead of directly sharing the collection
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
        
        # Check if user is already shared with the collection
        if collection.shared_with.filter(id=user.id).exists():
            return Response({"error": "Collection is already shared with this user"}, status=400)
        
        # Check if there's already a pending invite for this user
        if CollectionInvite.objects.filter(collection=collection, invited_user=user).exists():
            return Response({"error": "Invite already sent to this user"}, status=400)
        
        # Create the invite instead of directly sharing
        invite = CollectionInvite.objects.create(
            collection=collection,
            invited_user=user
        )
        
        return Response({"success": f"Invite sent to {user.username}"})
    
    # Custom action to list all invites for a user
    @action(detail=False, methods=['get'], url_path='invites')
    def invites(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        
        invites = CollectionInvite.objects.filter(invited_user=request.user)
        serializer = CollectionInviteSerializer(invites, many=True)
        
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='revoke-invite/(?P<uuid>[^/.]+)')
    def revoke_invite(self, request, pk=None, uuid=None):
        """Revoke a pending invite for a collection"""
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        
        collection = self.get_object()
        
        if not uuid:
            return Response({"error": "User UUID is required"}, status=400)
        
        try:
            user = User.objects.get(uuid=uuid, public_profile=True)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        
        # Only collection owner can revoke invites
        if collection.user != request.user:
            return Response({"error": "Only collection owner can revoke invites"}, status=403)
        
        try:
            invite = CollectionInvite.objects.get(collection=collection, invited_user=user)
            invite.delete()
            return Response({"success": f"Invite revoked for {user.username}"})
        except CollectionInvite.DoesNotExist:
            return Response({"error": "No pending invite found for this user"}, status=404)

    @action(detail=True, methods=['post'], url_path='accept-invite')
    def accept_invite(self, request, pk=None):
        """Accept a collection invite"""
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        
        collection = self.get_object()
        
        try:
            invite = CollectionInvite.objects.get(collection=collection, invited_user=request.user)
        except CollectionInvite.DoesNotExist:
            return Response({"error": "No pending invite found for this collection"}, status=404)
        
        # Add user to collection's shared_with
        collection.shared_with.add(request.user)
        
        # Delete the invite
        invite.delete()
        
        return Response({"success": f"Successfully joined collection: {collection.name}"})

    @action(detail=True, methods=['post'], url_path='decline-invite')
    def decline_invite(self, request, pk=None):
        """Decline a collection invite"""
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        
        collection = self.get_object()
        
        try:
            invite = CollectionInvite.objects.get(collection=collection, invited_user=request.user)
            invite.delete()
            return Response({"success": f"Declined invite for collection: {collection.name}"})
        except CollectionInvite.DoesNotExist:
            return Response({"error": "No pending invite found for this collection"}, status=404)
    
    # Action to list all users a collection **can** be shared with, excluding those already shared with and those with pending invites
    @action(detail=True, methods=['get'], url_path='can-share')
    def can_share(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        
        collection = self.get_object()
        
        # Get users with pending invites and users already shared with
        users_with_pending_invites = set(str(uuid) for uuid in CollectionInvite.objects.filter(collection=collection).values_list('invited_user__uuid', flat=True))
        users_already_shared = set(str(uuid) for uuid in collection.shared_with.values_list('uuid', flat=True))

        # Get all users with public profiles excluding only the owner
        all_users = User.objects.filter(public_profile=True).exclude(id=request.user.id)
        
        # Return fully serialized user data with status
        serializer = UserSerializer(all_users, many=True)
        result_data = []
        for user_data in serializer.data:
            user_data.pop('has_password', None)
            user_data.pop('disable_password', None)
            # Add status field
            if user_data['uuid'] in users_with_pending_invites:
                user_data['status'] = 'pending'
            elif user_data['uuid'] in users_already_shared:
                user_data['status'] = 'shared'
            else:
                user_data['status'] = 'available'
            result_data.append(user_data)
        
        return Response(result_data)

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
        
        # Remove user from shared_with
        collection.shared_with.remove(user)
        
        # Handle locations owned by the unshared user that are in this collection
        # These locations should be removed from the collection since they lose access
        locations_to_remove = collection.locations.filter(user=user)
        removed_count = locations_to_remove.count()
        
        if locations_to_remove.exists():
            # Remove these locations from the collection
            collection.locations.remove(*locations_to_remove)
        
        collection.save()
        
        success_message = f"Unshared with {user.username}"
        if removed_count > 0:
            success_message += f" and removed {removed_count} location(s) they owned from the collection"
        
        return Response({"success": success_message})
    
    # Action for a shared user to leave a collection
    @action(detail=True, methods=['post'], url_path='leave')
    def leave(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        
        collection = self.get_object()
        
        if request.user == collection.user:
            return Response({"error": "Owner cannot leave their own collection"}, status=400)
        
        if not collection.shared_with.filter(id=request.user.id).exists():
            return Response({"error": "You are not a member of this collection"}, status=400)
        
        # Remove the user from shared_with
        collection.shared_with.remove(request.user)
        
        # Handle locations owned by the user that are in this collection
        locations_to_remove = collection.locations.filter(user=request.user)
        removed_count = locations_to_remove.count()
        
        if locations_to_remove.exists():
            # Remove these locations from the collection
            collection.locations.remove(*locations_to_remove)
        
        collection.save()
        
        success_message = f"You have left the collection: {collection.name}"
        if removed_count > 0:
            success_message += f" and removed {removed_count} location(s) you owned from the collection"
        
        return Response({"success": success_message})

    def perform_create(self, serializer):
        # This is ok because you cannot share a collection when creating it
        serializer.save(user=self.request.user)
    
    def paginate_and_respond(self, queryset, request):
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)