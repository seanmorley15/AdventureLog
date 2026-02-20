from django.db.models import Q, Prefetch
from django.db.models.functions import Lower
from django.db import transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework import status
from django.http import HttpResponse
from django.conf import settings
from django.core.files.base import ContentFile
import io
import os
import json
import zipfile
import tempfile
from adventures.models import Collection, Location, Transportation, Note, Checklist, ChecklistItem, CollectionInvite, ContentImage, CollectionItineraryItem, Lodging, CollectionItineraryDay, ContentAttachment, Category
from adventures.permissions import CollectionShared
from adventures.serializers import CollectionSerializer, CollectionInviteSerializer, UltraSlimCollectionSerializer, CollectionItineraryItemSerializer, CollectionItineraryDaySerializer
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
            if order_direction == 'asc':
                ordering = f'-{ordering}'
        elif order_by == 'start_date':
            ordering = 'start_date'
            if order_direction == 'desc':
                ordering = 'start_date'
            else:
                ordering = '-start_date'
        else:
            order_by == 'updated_at'
            ordering = 'updated_at'
            if order_direction == 'desc':
                ordering = '-updated_at'

        return queryset.order_by(ordering)
    
    def apply_status_filter(self, queryset):
        """Apply status filtering based on query parameter"""
        from datetime import date
        status_filter = self.request.query_params.get('status', None)
        
        if not status_filter:
            return queryset
        
        today = date.today()
        
        if status_filter == 'folder':
            # Collections without dates
            return queryset.filter(Q(start_date__isnull=True) | Q(end_date__isnull=True))
        elif status_filter == 'upcoming':
            # Start date in the future
            return queryset.filter(start_date__gt=today)
        elif status_filter == 'in_progress':
            # Currently ongoing
            return queryset.filter(start_date__lte=today, end_date__gte=today)
        elif status_filter == 'completed':
            # End date in the past
            return queryset.filter(end_date__lt=today)
        
        return queryset
    
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
        return self.get_base_queryset().select_related('user', 'primary_image').prefetch_related(
            Prefetch(
                'locations__images',
                queryset=ContentImage.objects.filter(is_primary=True).select_related('user'),
                to_attr='primary_images'
            ),
            'shared_with'
        )

    def get_base_queryset(self):
        """Base queryset logic extracted for reuse"""
        if self.action == 'destroy':
            queryset = Collection.objects.filter(user=self.request.user.id)
        elif self.action in ['update', 'partial_update', 'leave']:
            queryset = Collection.objects.filter(
                Q(user=self.request.user.id) | Q(shared_with=self.request.user)
            ).distinct()
        # Allow access to collections with pending invites for accept/decline actions
        elif self.action in ['accept_invite', 'decline_invite']:
            if not self.request.user.is_authenticated:
                queryset = Collection.objects.none()
            else:
                queryset = Collection.objects.filter(
                    Q(user=self.request.user.id)
                    | Q(shared_with=self.request.user)
                    | Q(invites__invited_user=self.request.user)
                ).distinct()
        elif self.action == 'retrieve':
            if not self.request.user.is_authenticated:
                queryset = Collection.objects.filter(is_public=True)
            else:
                queryset = Collection.objects.filter(
                    Q(is_public=True)
                    | Q(user=self.request.user.id)
                    | Q(shared_with=self.request.user)
                ).distinct()
        else:
            # For list action and default base queryset, return collections owned by the user (exclude shared)
            queryset = Collection.objects.filter(
                Q(user=self.request.user.id) & Q(is_archived=False)
            ).distinct()

        return queryset.select_related('primary_image').prefetch_related('shared_with')

    def get_queryset(self):
        """Get queryset with optimizations for list actions"""
        if self.action in ['list', 'all', 'archived', 'shared']:
            return self.get_optimized_queryset_for_listing()
        return self.get_base_queryset()
    
    def list(self, request):
        # make sure the user is authenticated
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        
        # List should only return collections owned by the requesting user (shared collections are available
        # via the `shared` action).
        queryset = Collection.objects.filter(
            Q(user=request.user.id) & Q(is_archived=False)
        ).distinct().select_related('user', 'primary_image').prefetch_related(
            Prefetch(
                'locations__images',
                queryset=ContentImage.objects.filter(is_primary=True).select_related('user'),
                to_attr='primary_images'
            )
        )
        
        queryset = self.apply_status_filter(queryset)
        queryset = self.apply_sorting(queryset)
        return self.paginate_and_respond(queryset, request)
    
    @action(detail=False, methods=['get'])
    def all(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
       
        queryset = Collection.objects.filter(
            Q(user=request.user)
        ).select_related('user', 'primary_image').prefetch_related(
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
        ).select_related('user', 'primary_image').prefetch_related(
            Prefetch(
                'locations__images',
                queryset=ContentImage.objects.filter(is_primary=True).select_related('user'),
                to_attr='primary_images'
            )
        )
        
        queryset = self.apply_sorting(queryset)
        serializer = self.get_serializer(queryset, many=True)
       
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """Retrieve a collection and include itinerary items and day metadata in the response."""
        collection = self.get_object()
        serializer = self.get_serializer(collection)
        data = serializer.data

        # Include itinerary items inline with collection details
        itinerary_items = CollectionItineraryItem.objects.filter(collection=collection)
        itinerary_serializer = CollectionItineraryItemSerializer(itinerary_items, many=True)
        data['itinerary'] = itinerary_serializer.data
        
        # Include itinerary day metadata
        itinerary_days = CollectionItineraryDay.objects.filter(collection=collection)
        days_serializer = CollectionItineraryDaySerializer(itinerary_days, many=True)
        data['itinerary_days'] = days_serializer.data

        return Response(data)
    
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

    @action(detail=True, methods=['get'], url_path='export')
    def export_collection(self, request, pk=None):
        """Export a single collection and its related content as a ZIP file."""
        collection = self.get_object()

        export_data = {
            'version': getattr(settings, 'ADVENTURELOG_RELEASE_VERSION', 'unknown'),
            # Omit export_date to keep template-friendly exports (no dates)
            'collection': {
                'id': str(collection.id),
                'name': collection.name,
                'description': collection.description,
                'is_public': collection.is_public,
                # Omit start/end dates
                'link': collection.link,
            },
            'locations': [],
            'transportation': [],
            'notes': [],
            'checklists': [],
            'lodging': [],
            # Omit itinerary_items entirely
            'images': [],
            'attachments': [],
            'primary_image_ref': None,
        }

        image_export_map = {}

        for loc in collection.locations.all().select_related('city', 'region', 'country'):
            loc_entry = {
                'id': str(loc.id),
                'name': loc.name,
                'description': loc.description,
                'location': loc.location,
                'tags': loc.tags or [],
                'rating': loc.rating,
                'link': loc.link,
                'is_public': loc.is_public,
                'longitude': float(loc.longitude) if loc.longitude is not None else None,
                'latitude': float(loc.latitude) if loc.latitude is not None else None,
                'city': loc.city.name if loc.city else None,
                'region': loc.region.name if loc.region else None,
                'country': loc.country.name if loc.country else None,
                'images': [],
                'attachments': [],
            }

            for img in loc.images.all():
                img_export_id = f"img_{len(export_data['images'])}"
                image_export_map[str(img.id)] = img_export_id
                export_data['images'].append({
                    'export_id': img_export_id,
                    'id': str(img.id),
                    'name': os.path.basename(getattr(img.image, 'name', 'image')),
                    'is_primary': getattr(img, 'is_primary', False),
                })
                loc_entry['images'].append(img_export_id)

            for att in loc.attachments.all():
                att_export_id = f"att_{len(export_data['attachments'])}"
                export_data['attachments'].append({
                    'export_id': att_export_id,
                    'id': str(att.id),
                    'name': os.path.basename(getattr(att.file, 'name', 'attachment')),
                })
                loc_entry['attachments'].append(att_export_id)

            export_data['locations'].append(loc_entry)

        if collection.primary_image:
            export_data['primary_image_ref'] = image_export_map.get(str(collection.primary_image.id))

        # Related content (if models have FK to collection)
        for t in Transportation.objects.filter(collection=collection):
            export_data['transportation'].append({
                'id': str(t.id),
                'type': getattr(t, 'transportation_type', None),
                'name': getattr(t, 'name', None),
                # Omit date
                'notes': getattr(t, 'notes', None),
            })
        for n in Note.objects.filter(collection=collection):
            export_data['notes'].append({
                'id': str(n.id),
                'title': getattr(n, 'title', None),
                'content': getattr(n, 'content', ''),
                # Omit created_at
            })
        for c in Checklist.objects.filter(collection=collection):
            items = []
            if hasattr(c, 'items'):
                items = [
                    {
                        'name': getattr(item, 'name', None),
                        'completed': getattr(item, 'completed', False),
                    } for item in c.items.all()
                ]
            export_data['checklists'].append({
                'id': str(c.id),
                'name': getattr(c, 'name', None),
                'items': items,
            })
        for l in Lodging.objects.filter(collection=collection):
            export_data['lodging'].append({
                'id': str(l.id),
                'type': getattr(l, 'lodging_type', None),
                'name': getattr(l, 'name', None),
                # Omit start_date/end_date
                'notes': getattr(l, 'notes', None),
            })
        # Intentionally omit itinerary_items from export

        # Create ZIP in temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            with zipfile.ZipFile(tmp_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.writestr('metadata.json', json.dumps(export_data, indent=2))

                # Write image files
                for loc in collection.locations.all():
                    for img in loc.images.all():
                        export_id = image_export_map.get(str(img.id))
                        if not export_id:
                            continue
                        try:
                            file_name = os.path.basename(getattr(img.image, 'name', 'image'))
                            storage = getattr(img.image, 'storage', None)
                            if storage:
                                with storage.open(img.image.name, 'rb') as f:
                                    zipf.writestr(f'images/{export_id}-{file_name}', f.read())
                            elif hasattr(img.image, 'path'):
                                with open(img.image.path, 'rb') as f:
                                    zipf.writestr(f'images/{export_id}-{file_name}', f.read())
                        except Exception:
                            continue

                # Write attachment files
                for loc in collection.locations.all():
                    for att in loc.attachments.all():
                        try:
                            file_name = os.path.basename(getattr(att.file, 'name', 'attachment'))
                            storage = getattr(att.file, 'storage', None)
                            if storage:
                                with storage.open(att.file.name, 'rb') as f:
                                    zipf.writestr(f'attachments/{file_name}', f.read())
                            elif hasattr(att.file, 'path'):
                                with open(att.file.path, 'rb') as f:
                                    zipf.writestr(f'attachments/{file_name}', f.read())
                        except Exception:
                            continue

            with open(tmp_file.name, 'rb') as fh:
                data = fh.read()
            os.unlink(tmp_file.name)

        filename = f"collection-{collection.name.replace(' ', '_')}.zip"
        response = HttpResponse(data, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=['post'], url_path='import', parser_classes=[MultiPartParser])
    def import_collection(self, request):
        """Import a single collection from a ZIP file. Handles name conflicts by appending (n)."""
        upload = request.FILES.get('file')
        if not upload:
            return Response({'detail': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Read zip
        file_bytes = upload.read()
        with zipfile.ZipFile(io.BytesIO(file_bytes), 'r') as zipf:
            try:
                metadata = json.loads(zipf.read('metadata.json').decode('utf-8'))
            except KeyError:
                return Response({'detail': 'metadata.json missing'}, status=status.HTTP_400_BAD_REQUEST)

            base_name = (metadata.get('collection') or {}).get('name') or 'Imported Collection'

            # Ensure unique name per user
            existing_names = set(request.user.collection_set.values_list('name', flat=True))
            unique_name = base_name
            if unique_name in existing_names:
                i = 1
                while True:
                    candidate = f"{base_name} ({i})"
                    if candidate not in existing_names:
                        unique_name = candidate
                        break
                    i += 1

            new_collection = Collection.objects.create(
                user=request.user,
                name=unique_name,
                description=(metadata.get('collection') or {}).get('description'),
                is_public=(metadata.get('collection') or {}).get('is_public', False),
                start_date=__import__('datetime').date.fromisoformat((metadata.get('collection') or {}).get('start_date')) if (metadata.get('collection') or {}).get('start_date') else None,
                end_date=__import__('datetime').date.fromisoformat((metadata.get('collection') or {}).get('end_date')) if (metadata.get('collection') or {}).get('end_date') else None,
                link=(metadata.get('collection') or {}).get('link'),
            )

            image_export_map = {img['export_id']: img for img in metadata.get('images', [])}
            attachment_export_map = {att['export_id']: att for att in metadata.get('attachments', [])}

            # Import locations
            for loc_data in metadata.get('locations', []):
                cat_obj = None
                if loc_data.get('category'):
                    cat_obj, _ = Category.objects.get_or_create(user=request.user, name=loc_data['category'])
                # Attempt to find a very similar existing location for this user
                from difflib import SequenceMatcher

                def _ratio(a, b):
                    a = (a or '').strip().lower()
                    b = (b or '').strip().lower()
                    if not a and not b:
                        return 1.0
                    return SequenceMatcher(None, a, b).ratio()

                def _coords_close(lat1, lon1, lat2, lon2, threshold=0.02):
                    try:
                        if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
                            return False
                        return abs(float(lat1) - float(lat2)) <= threshold and abs(float(lon1) - float(lon2)) <= threshold
                    except Exception:
                        return False

                incoming_name = loc_data.get('name') or 'Untitled'
                incoming_location_text = loc_data.get('location')
                incoming_lat = loc_data.get('latitude')
                incoming_lon = loc_data.get('longitude')

                existing_loc = None
                best_score = 0.0
                for cand in Location.objects.filter(user=request.user):
                    name_score = _ratio(incoming_name, cand.name)
                    loc_text_score = _ratio(incoming_location_text, getattr(cand, 'location', None))
                    close_coords = _coords_close(incoming_lat, incoming_lon, cand.latitude, cand.longitude)
                    # Define "very similar": strong name match OR decent name with location/coords match
                    combined_score = max(name_score, (name_score + loc_text_score) / 2.0)
                    if close_coords:
                        combined_score = max(combined_score, name_score + 0.1)  # small boost for coord proximity
                    if combined_score > best_score and (
                        name_score >= 0.92 or (name_score >= 0.85 and (loc_text_score >= 0.85 or close_coords))
                    ):
                        best_score = combined_score
                        existing_loc = cand

                if existing_loc:
                    # Link existing location to the new collection, skip creating a duplicate
                    loc = existing_loc
                    loc.collections.add(new_collection)
                    created_new_loc = False
                else:
                    # Create a brand-new location
                    loc = Location.objects.create(
                        user=request.user,
                        name=incoming_name,
                        description=loc_data.get('description'),
                        location=incoming_location_text,
                        tags=loc_data.get('tags') or [],
                        rating=loc_data.get('rating'),
                        link=loc_data.get('link'),
                        is_public=bool(loc_data.get('is_public', False)),
                        longitude=incoming_lon,
                        latitude=incoming_lat,
                        category=cat_obj,
                    )
                    loc.collections.add(new_collection)
                    created_new_loc = True

                # Images
                # Only import images for newly created locations to avoid duplicating user content
                if created_new_loc:
                    for export_id in loc_data.get('images', []):
                        img_meta = image_export_map.get(export_id)
                        if not img_meta:
                            continue
                        prefix = f"images/{export_id}-"
                        member = next((m for m in zipf.namelist() if m.startswith(prefix)), None)
                        if not member:
                            continue
                        file_bytes_img = zipf.read(member)
                        file_name_img = os.path.basename(member)
                        from django.core.files.base import ContentFile
                        image_obj = ContentImage(
                            user=request.user,
                            image=ContentFile(file_bytes_img, name=file_name_img),
                        )
                        # Assign to the generic relation for Location
                        image_obj.content_object = loc
                        image_obj.save()
                        if img_meta.get('is_primary'):
                            new_collection.primary_image = image_obj
                            new_collection.save(update_fields=['primary_image'])

                # Attachments
                if created_new_loc:
                    for export_id in loc_data.get('attachments', []):
                        att_meta = attachment_export_map.get(export_id)
                        if not att_meta:
                            continue
                        file_name_att = att_meta.get('name', '')
                        member = next((m for m in zipf.namelist() if m == f"attachments/{file_name_att}"), None)
                        if not member:
                            continue
                        file_bytes_att = zipf.read(member)
                        from django.core.files.base import ContentFile
                        attachment_obj = ContentAttachment(
                            user=request.user,
                            file=ContentFile(file_bytes_att, name=file_name_att),
                        )
                        # Assign to the generic relation for Location
                        attachment_obj.content_object = loc
                        attachment_obj.save()

            serializer = self.get_serializer(new_collection)
            return Response(serializer.data, status=status.HTTP_201_CREATED)


    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Create a duplicate of an existing collection.

        Copies collection metadata and linked content:
        - locations (linked, not cloned)
        - transportation, notes, checklists (with items), lodging
        - itinerary days and itinerary items
        Shared users are not copied and the new collection is private.
        """
        original = self.get_object()

        # Only the owner can duplicate
        if original.user != request.user:
            return Response(
                {"error": "You do not have permission to duplicate this collection."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            with transaction.atomic():
                new_collection = Collection.objects.create(
                    user=request.user,
                    name=f"Copy of {original.name}",
                    description=original.description,
                    link=original.link,
                    is_public=False,
                    is_archived=False,
                    start_date=original.start_date,
                    end_date=original.end_date,
                )

                # Link existing locations to the new collection
                linked_locations = list(original.locations.all())
                if linked_locations:
                    new_collection.locations.set(linked_locations)

                # Duplicate primary image if it exists so permissions align with the new collection
                if original.primary_image:
                    original_primary = original.primary_image
                    if original_primary.image:
                        try:
                            original_primary.image.open('rb')
                            image_bytes = original_primary.image.read()
                        finally:
                            try:
                                original_primary.image.close()
                            except Exception:
                                pass

                        file_name = (original_primary.image.name or '').split('/')[-1] or 'image.webp'
                        new_primary = ContentImage(
                            user=request.user,
                            image=ContentFile(image_bytes, name=file_name),
                            immich_id=None,
                            is_primary=original_primary.is_primary,
                        )
                    else:
                        new_primary = ContentImage(
                            user=request.user,
                            immich_id=original_primary.immich_id,
                            is_primary=original_primary.is_primary,
                        )

                    new_primary.content_object = new_collection
                    new_primary.save()
                    new_collection.primary_image = new_primary
                    new_collection.save(update_fields=['primary_image'])

                def _copy_generic_media(source_obj, target_obj):
                    # Images
                    for img in source_obj.images.all():
                        if img.image:
                            try:
                                img.image.open('rb')
                                image_bytes = img.image.read()
                            finally:
                                try:
                                    img.image.close()
                                except Exception:
                                    pass

                            file_name = (img.image.name or '').split('/')[-1] or 'image.webp'
                            media = ContentImage(
                                user=request.user,
                                image=ContentFile(image_bytes, name=file_name),
                                immich_id=None,
                                is_primary=img.is_primary,
                            )
                        else:
                            media = ContentImage(
                                user=request.user,
                                immich_id=img.immich_id,
                                is_primary=img.is_primary,
                            )

                        media.content_object = target_obj
                        media.save()

                    # Attachments
                    for attachment in source_obj.attachments.all():
                        try:
                            attachment.file.open('rb')
                            file_bytes = attachment.file.read()
                        finally:
                            try:
                                attachment.file.close()
                            except Exception:
                                pass

                        file_name = (attachment.file.name or '').split('/')[-1] or 'attachment'
                        new_attachment = ContentAttachment(
                            user=request.user,
                            file=ContentFile(file_bytes, name=file_name),
                            name=attachment.name,
                        )
                        new_attachment.content_object = target_obj
                        new_attachment.save()

                # Copy FK-based related content and track ID mapping for itinerary relinks
                object_id_map = {}

                for item in Transportation.objects.filter(collection=original):
                    new_item = Transportation.objects.create(
                        user=request.user,
                        collection=new_collection,
                        type=item.type,
                        name=item.name,
                        description=item.description,
                        rating=item.rating,
                        price=item.price,
                        link=item.link,
                        date=item.date,
                        end_date=item.end_date,
                        start_timezone=item.start_timezone,
                        end_timezone=item.end_timezone,
                        flight_number=item.flight_number,
                        from_location=item.from_location,
                        origin_latitude=item.origin_latitude,
                        origin_longitude=item.origin_longitude,
                        destination_latitude=item.destination_latitude,
                        destination_longitude=item.destination_longitude,
                        start_code=item.start_code,
                        end_code=item.end_code,
                        to_location=item.to_location,
                        is_public=item.is_public,
                    )
                    object_id_map[item.id] = new_item.id
                    _copy_generic_media(item, new_item)

                for item in Note.objects.filter(collection=original):
                    new_item = Note.objects.create(
                        user=request.user,
                        collection=new_collection,
                        name=item.name,
                        content=item.content,
                        links=item.links,
                        date=item.date,
                        is_public=item.is_public,
                    )
                    object_id_map[item.id] = new_item.id
                    _copy_generic_media(item, new_item)

                for item in Lodging.objects.filter(collection=original):
                    new_item = Lodging.objects.create(
                        user=request.user,
                        collection=new_collection,
                        name=item.name,
                        type=item.type,
                        description=item.description,
                        rating=item.rating,
                        link=item.link,
                        check_in=item.check_in,
                        check_out=item.check_out,
                        timezone=item.timezone,
                        reservation_number=item.reservation_number,
                        price=item.price,
                        latitude=item.latitude,
                        longitude=item.longitude,
                        location=item.location,
                        is_public=item.is_public,
                    )
                    object_id_map[item.id] = new_item.id
                    _copy_generic_media(item, new_item)

                for checklist in Checklist.objects.filter(collection=original):
                    new_checklist = Checklist.objects.create(
                        user=request.user,
                        collection=new_collection,
                        name=checklist.name,
                        date=checklist.date,
                        is_public=checklist.is_public,
                    )
                    object_id_map[checklist.id] = new_checklist.id

                    for checklist_item in checklist.checklistitem_set.all():
                        ChecklistItem.objects.create(
                            user=request.user,
                            checklist=new_checklist,
                            name=checklist_item.name,
                            is_checked=checklist_item.is_checked,
                        )

                # Copy itinerary day metadata
                for day in CollectionItineraryDay.objects.filter(collection=original):
                    CollectionItineraryDay.objects.create(
                        collection=new_collection,
                        date=day.date,
                        name=day.name,
                        description=day.description,
                    )

                # Copy itinerary items and relink to duplicated FK-based content where applicable
                for item in CollectionItineraryItem.objects.filter(collection=original):
                    CollectionItineraryItem.objects.create(
                        collection=new_collection,
                        content_type=item.content_type,
                        object_id=object_id_map.get(item.object_id, item.object_id),
                        date=item.date,
                        is_global=item.is_global,
                        order=item.order,
                    )

            serializer = self.get_serializer(new_collection)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to duplicate collection %s", pk)
            return Response(
                {"error": "An error occurred while duplicating the collection."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def perform_create(self, serializer):
        # This is ok because you cannot share a collection when creating it
        serializer.save(user=self.request.user)
    
    def _cleanup_out_of_range_itinerary_items(self, collection):
        """Delete itinerary items and day metadata outside the collection's date range."""
        if not collection.start_date or not collection.end_date:
            # If no date range is set, don't delete anything
            return
        
        # Delete itinerary items outside the date range
        deleted_items = CollectionItineraryItem.objects.filter(
            collection=collection
        ).exclude(
            date__range=[collection.start_date, collection.end_date]
        ).delete()
        
        # Delete day metadata outside the date range
        deleted_days = CollectionItineraryDay.objects.filter(
            collection=collection
        ).exclude(
            date__range=[collection.start_date, collection.end_date]
        ).delete()
        
        return deleted_items, deleted_days
    
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """Override update to handle is_public cascading and clean up out-of-range itinerary items when dates change."""
        instance = self.get_object()
        old_is_public = instance.is_public
        old_start_date = instance.start_date
        old_end_date = instance.end_date
        
        # Perform the standard update
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Check if is_public changed
        new_is_public = serializer.instance.is_public
        is_public_changed = old_is_public != new_is_public
        
        # Handle is_public cascading
        if is_public_changed:
            if new_is_public:
                # Collection is being made public, update all linked items to public
                serializer.instance.locations.filter(is_public=False).update(is_public=True)
                serializer.instance.transportation_set.filter(is_public=False).update(is_public=True)
                serializer.instance.note_set.filter(is_public=False).update(is_public=True)
                serializer.instance.checklist_set.filter(is_public=False).update(is_public=True)
                serializer.instance.lodging_set.filter(is_public=False).update(is_public=True)
            else:
                # Collection is being made private, check each linked item
                # Only set an item to private if it doesn't belong to any other public collection
                
                # Handle locations (many-to-many relationship)
                locations_in_collection = serializer.instance.locations.filter(is_public=True)
                for location in locations_in_collection:
                    # Check if this location belongs to any other public collection
                    has_other_public_collection = location.collections.filter(
                        is_public=True
                    ).exclude(id=serializer.instance.id).exists()
                    if not has_other_public_collection:
                        location.is_public = False
                        location.save(update_fields=['is_public'])
                
                # Handle transportations, notes, checklists, lodging (foreign key relationships)
                # Transportation
                transportations_to_check = serializer.instance.transportation_set.filter(is_public=True)
                for transportation in transportations_to_check:
                    transportation.is_public = False
                    transportation.save(update_fields=['is_public'])
                
                # Notes
                notes_to_check = serializer.instance.note_set.filter(is_public=True)
                for note in notes_to_check:
                    note.is_public = False
                    note.save(update_fields=['is_public'])
                
                # Checklists
                checklists_to_check = serializer.instance.checklist_set.filter(is_public=True)
                for checklist in checklists_to_check:
                    checklist.is_public = False
                    checklist.save(update_fields=['is_public'])
                
                # Lodging
                lodging_to_check = serializer.instance.lodging_set.filter(is_public=True)
                for lodging in lodging_to_check:
                    lodging.is_public = False
                    lodging.save(update_fields=['is_public'])
        
        # Check if dates changed
        new_start_date = serializer.instance.start_date
        new_end_date = serializer.instance.end_date
        
        dates_changed = (old_start_date != new_start_date or old_end_date != new_end_date)
        
        # Clean up out-of-range items if dates changed
        if dates_changed:
            self._cleanup_out_of_range_itinerary_items(serializer.instance)
        
        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}
        
        return Response(serializer.data)
    
    def paginate_and_respond(self, queryset, request):
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)