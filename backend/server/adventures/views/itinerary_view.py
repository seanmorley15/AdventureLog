from adventures.models import Location, Collection, CollectionItineraryItem, Transportation, Note, Lodging, Visit, Checklist, Note, CollectionItineraryDay
import datetime
from django.utils.dateparse import parse_date, parse_datetime
from django.contrib.contenttypes.models import ContentType
from django.db import models
from adventures.serializers import CollectionItineraryItemSerializer, CollectionItineraryDaySerializer
from adventures.utils.itinerary import reorder_itinerary_items
from adventures.utils.autogenerate_itinerary import auto_generate_itinerary
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def get_collection_users(collection):
    """Get all users associated with a collection (owner + shared_with)."""
    users = [collection.user]
    users.extend(collection.shared_with.all())
    return users


def create_visits_for_users(users, parent_object, parent_type, start_date, end_date, collection=None, notes=None):
    """
    Create or extend visits for all specified users on the given parent object.

    For consecutive days, this merges visits into a single extended visit.
    Example: Lodging on Day 1, 2, 3 → one visit spanning all 3 days

    Args:
        users: List of User objects
        parent_object: Location, Transportation, or Lodging instance
        parent_type: 'location', 'transportation', or 'lodging'
        start_date: datetime for visit start
        end_date: datetime for visit end
        collection: Optional Collection this visit was created from
        notes: Optional notes for the visit

    Returns:
        List of created/updated Visit objects
    """
    created_visits = []

    for user in users:
        # Get existing visits for this user and parent
        if parent_type == 'location':
            existing_visits = Visit.objects.filter(location=parent_object, user=user)
        elif parent_type == 'transportation':
            existing_visits = Visit.objects.filter(transportation=parent_object, user=user)
        elif parent_type == 'lodging':
            existing_visits = Visit.objects.filter(lodging=parent_object, user=user)
        else:
            continue

        # Check for exact overlap (same start date) - update existing
        exact_match = existing_visits.filter(start_date__date=start_date.date()).first()
        if exact_match:
            # Only extend end_date if new one is later
            if end_date > exact_match.end_date:
                exact_match.end_date = end_date
                exact_match.save(update_fields=['end_date'])
            # Update collection reference if provided
            if collection and not exact_match.collection:
                exact_match.collection = collection
                exact_match.save(update_fields=['collection'])
            created_visits.append(exact_match)
            logger.info(f"Updated exact match visit {exact_match.id} for user {user.username}")
            continue

        # Check for adjacent visit ending the day before (extend it)
        day_before = start_date.date() - datetime.timedelta(days=1)
        adjacent_before = existing_visits.filter(end_date__date=day_before).first()

        if adjacent_before:
            # Extend the existing visit's end date
            adjacent_before.end_date = end_date
            adjacent_before.save(update_fields=['end_date'])
            created_visits.append(adjacent_before)
            logger.info(f"Extended visit {adjacent_before.id} end_date for user {user.username}")
            continue

        # Check for adjacent visit starting the day after (extend it backwards)
        day_after = end_date.date() + datetime.timedelta(days=1)
        adjacent_after = existing_visits.filter(start_date__date=day_after).first()

        if adjacent_after:
            # Extend the existing visit's start date
            adjacent_after.start_date = start_date
            adjacent_after.save(update_fields=['start_date'])
            created_visits.append(adjacent_after)
            logger.info(f"Extended visit {adjacent_after.id} start_date for user {user.username}")
            continue

        # No adjacent visit found, create a new one
        visit_kwargs = {
            'user': user,
            'start_date': start_date,
            'end_date': end_date,
            'notes': notes or "Created from itinerary planning",
            'collection': collection,
        }

        if parent_type == 'location':
            visit_kwargs['location'] = parent_object
        elif parent_type == 'transportation':
            visit_kwargs['transportation'] = parent_object
        elif parent_type == 'lodging':
            visit_kwargs['lodging'] = parent_object

        visit = Visit.objects.create(**visit_kwargs)
        created_visits.append(visit)
        logger.info(f"Created new visit {visit.id} for user {user.username}")

    return created_visits

class ItineraryViewSet(viewsets.ModelViewSet):
    serializer_class = CollectionItineraryItemSerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess]

    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return CollectionItineraryItem.objects.none()
        
        # Return itinerary items from collections the user owns or is shared with
        return CollectionItineraryItem.objects.filter(
            Q(collection__user=user) | Q(collection__shared_with=user)
        ).distinct().select_related('collection', 'collection__user').order_by('date', 'order')

    def create(self, request, *args, **kwargs):
        """
        Accept 'content_type' as either a ContentType PK or a model name string
        (e.g. 'location', 'lodging', 'transportation', 'note', 'visit'). If a
        string is provided we resolve it to the appropriate ContentType PK and
        validate the referenced object exists and the user has permission to
        access it.
        
        Optional parameter 'update_item_date': if True, update the actual item's
        date field to match the itinerary date.
        """
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data.copy()
        content_type_val = data.get('content_type')
        object_id = data.get('object_id')
        update_item_date = data.get('update_item_date', False)
        target_date = data.get('date')
        is_global = data.get('is_global', False)
        # Normalize is_global to boolean
        if isinstance(is_global, str):
            is_global = is_global.lower() in ['1', 'true', 'yes']
        data['is_global'] = is_global

        # Support legacy field 'location' -> treat as content_type='location'
        if not content_type_val and data.get('location'):
            content_type_val = 'location'
            object_id = object_id or data.get('location')
            data['content_type'] = content_type_val
            data['object_id'] = object_id

        # If content_type is provided as a string model name, map to ContentType PK
        if content_type_val and isinstance(content_type_val, str):
            # If it's already numeric-like, leave it
            if not content_type_val.isdigit():
                content_map = {
                    'location': Location,
                    'transportation': Transportation,
                    'note': Note,
                    'lodging': Lodging,
                    'visit': Visit,
                    'checklist': Checklist,
                    'note': Note,
                }

                if content_type_val not in content_map:
                    return Response({
                        'error': f"Invalid content_type. Must be one of: {', '.join(content_map.keys())}"
                    }, status=status.HTTP_400_BAD_REQUEST)

                model_class = content_map[content_type_val]

                # Validate referenced object exists
                try:
                    content_object = model_class.objects.get(id=object_id)
                except (ValueError, model_class.DoesNotExist):
                    return Response({'error': f"{content_type_val} not found"}, status=status.HTTP_404_NOT_FOUND)

                # Permission check
                permission_checker = IsOwnerOrSharedWithFullAccess()
                if not permission_checker.has_object_permission(request, self, content_object):
                    return Response({'error': 'User does not have permission to access this content'}, status=status.HTTP_403_FORBIDDEN)

                ct = ContentType.objects.get_for_model(model_class)
                data['content_type'] = ct.pk

                # Create visits when adding location/transportation/lodging to a dated itinerary
                # This happens regardless of update_item_date flag
                if target_date and content_object and content_type_val in ('location', 'transportation', 'lodging'):
                    clean_date = str(target_date).split('T')[0] if 'T' in str(target_date) else str(target_date)
                    logger.info(f"Creating visits for {content_type_val} {object_id} on date {clean_date}")

                    # Get collection and its users for creating visits
                    collection_id_for_visits = data.get('collection')
                    collection_users = []
                    if collection_id_for_visits:
                        try:
                            collection_obj = Collection.objects.get(id=collection_id_for_visits)
                            collection_users = get_collection_users(collection_obj)
                            logger.info(f"Collection {collection_obj.id} has {len(collection_users)} users: {[u.username for u in collection_users]}")
                        except Collection.DoesNotExist:
                            logger.warning(f"Collection {collection_id_for_visits} not found")
                    else:
                        logger.warning(f"No collection_id provided in request data")

                    if content_type_val == 'location':
                        # For locations, create an all-day visit for all collection users
                        start_input = data.get('start_date') or clean_date
                        end_input = data.get('end_date') or clean_date

                        def parse_bounds(val):
                            if not val:
                                return None
                            s = str(val)
                            if 'T' in s:
                                dt = parse_datetime(s)
                                return dt
                            d = parse_date(s)
                            if d:
                                return d
                            return None

                        parsed_start = parse_bounds(start_input)
                        parsed_end = parse_bounds(end_input)

                        if isinstance(parsed_start, datetime.date) and not isinstance(parsed_start, datetime.datetime):
                            new_start = datetime.datetime.combine(parsed_start, datetime.time.min)
                        elif isinstance(parsed_start, datetime.datetime):
                            new_start = parsed_start
                        else:
                            new_start = None

                        if isinstance(parsed_end, datetime.date) and not isinstance(parsed_end, datetime.datetime):
                            new_end = datetime.datetime.combine(parsed_end, datetime.time.max)
                        elif isinstance(parsed_end, datetime.datetime):
                            new_end = parsed_end
                        else:
                            new_end = None

                        if not new_start or not new_end:
                            try:
                                d = parse_date(clean_date)
                                new_start = datetime.datetime.combine(d, datetime.time.min)
                                new_end = datetime.datetime.combine(d, datetime.time.max)
                            except Exception:
                                new_start = None
                                new_end = None

                        if new_start and new_end:
                            # If source visit provided, update it (for drag-drop scenarios)
                            source_visit_id = data.get('source_visit_id')
                            if source_visit_id:
                                try:
                                    source_visit = Visit.objects.get(id=source_visit_id, location=content_object)
                                    source_visit.start_date = new_start
                                    source_visit.end_date = new_end
                                    source_visit.save(update_fields=['start_date', 'end_date'])
                                except Visit.DoesNotExist:
                                    pass

                            # Create visits for all collection users
                            if collection_users:
                                create_visits_for_users(
                                    users=collection_users,
                                    parent_object=content_object,
                                    parent_type='location',
                                    start_date=new_start,
                                    end_date=new_end,
                                    collection=collection_obj,
                                    notes="Created from itinerary planning"
                                )
                            else:
                                # Fallback: create single visit without user (legacy behavior)
                                exact_match = Visit.objects.filter(
                                    location=content_object,
                                    start_date=new_start,
                                    end_date=new_end
                                ).exists()

                                if not exact_match:
                                    overlap_q = Q(start_date__lte=new_end) & Q(end_date__gte=new_start)
                                    existing = Visit.objects.filter(location=content_object).filter(overlap_q).first()

                                    if existing:
                                        existing.start_date = new_start
                                        existing.end_date = new_end
                                        existing.save(update_fields=['start_date', 'end_date'])
                                    else:
                                        Visit.objects.create(
                                            location=content_object,
                                            start_date=new_start,
                                            end_date=new_end,
                                            notes="Created from itinerary planning"
                                        )

                    elif content_type_val == 'transportation':
                        # For transportation: create visits for all collection users
                        new_date = datetime.datetime.combine(parse_date(clean_date), datetime.time.min)
                        new_end_date = datetime.datetime.combine(parse_date(clean_date), datetime.time.max)

                        if collection_users:
                            create_visits_for_users(
                                users=collection_users,
                                parent_object=content_object,
                                parent_type='transportation',
                                start_date=new_date,
                                end_date=new_end_date,
                                collection=collection_obj,
                                notes="Created from itinerary planning"
                            )

                    elif content_type_val == 'lodging':
                        # For lodging: create full-day visits for all users
                        new_start = datetime.datetime.combine(parse_date(clean_date), datetime.time.min)
                        new_end = datetime.datetime.combine(parse_date(clean_date), datetime.time.max)

                        if collection_users:
                            create_visits_for_users(
                                users=collection_users,
                                parent_object=content_object,
                                parent_type='lodging',
                                start_date=new_start,
                                end_date=new_end,
                                collection=collection_obj,
                                notes="Created from itinerary planning"
                            )

                # For notes/checklists with update_item_date, update their date field
                if update_item_date and target_date and content_object and content_type_val not in ('location', 'transportation', 'lodging'):
                    clean_date = str(target_date).split('T')[0] if 'T' in str(target_date) else str(target_date)
                    date_field = None
                    if hasattr(content_object, 'date'):
                        date_field = 'date'
                    elif hasattr(content_object, 'start_date'):
                        date_field = 'start_date'

                    if date_field:
                        setattr(content_object, date_field, clean_date)
                        content_object.save(update_fields=[date_field])

        # Ensure order is unique for this collection+group combination (day or global)
        collection_id = data.get('collection')
        item_date = data.get('date')
        item_order = data.get('order', 0)
        
        # Basic XOR validation between date and is_global
        if is_global and item_date:
            return Response({'error': 'Global itinerary items must not include a date.'}, status=status.HTTP_400_BAD_REQUEST)
        if (not is_global) and not item_date:
            return Response({'error': 'Dated itinerary items must include a date.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate that the itinerary date (if provided) falls within the
        # collection's start_date/end_date range (if those bounds are set).
        if collection_id and item_date and not is_global:
            # Try parse date or datetime-like values
            parsed_date = None
            try:
                parsed_date = parse_date(str(item_date))
            except Exception:
                parsed_date = None
            if parsed_date is None:
                try:
                    dt = parse_datetime(str(item_date))
                    if dt:
                        parsed_date = dt.date()
                except Exception:
                    parsed_date = None

            if parsed_date is not None:
                try:
                    collection_obj = Collection.objects.get(id=collection_id)
                except Collection.DoesNotExist:
                    return Response({'error': 'Collection not found'}, status=status.HTTP_404_NOT_FOUND)

                if collection_obj.start_date and parsed_date < collection_obj.start_date:
                    return Response({'error': 'Itinerary item date is before the collection start_date'}, status=status.HTTP_400_BAD_REQUEST)
                if collection_obj.end_date and parsed_date > collection_obj.end_date:
                    return Response({'error': 'Itinerary item date is after the collection end_date'}, status=status.HTTP_400_BAD_REQUEST)

        if collection_id:
            if is_global:
                # Max order within global group
                existing_max = CollectionItineraryItem.objects.filter(
                    collection_id=collection_id,
                    is_global=True
                ).aggregate(max_order=models.Max('order'))['max_order']
                if existing_max is None:
                    existing_max = -1
                if item_order is None or item_order <= existing_max:
                    data['order'] = existing_max + 1
            elif item_date:
                # Find the maximum order for this collection+date
                existing_max = CollectionItineraryItem.objects.filter(
                    collection_id=collection_id,
                    date=item_date,
                    is_global=False
                ).aggregate(max_order=models.Max('order'))['max_order']
                
                # Check if the requested order conflicts with existing items
                if existing_max is not None and item_order <= existing_max:
                    # Assign next available order
                    data['order'] = existing_max + 1
        
        # Proceed with normal serializer flow using modified data
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # If we updated the item's date, include the updated object in response for frontend sync
        response_data = serializer.data
        if update_item_date and content_type_val and object_id:
            if content_type_val == 'transportation':
                try:
                    t = Transportation.objects.get(id=object_id)
                    from adventures.serializers import TransportationSerializer
                    response_data['updated_object'] = TransportationSerializer(t).data
                except Transportation.DoesNotExist:
                    pass
            elif content_type_val == 'lodging':
                try:
                    l = Lodging.objects.get(id=object_id)
                    from adventures.serializers import LodgingSerializer
                    response_data['updated_object'] = LodgingSerializer(l).data
                except Lodging.DoesNotExist:
                    pass
        
        headers = self.get_success_headers(serializer.data)
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)
    
    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """
        Override destroy to remove associated visits when deleting a location itinerary item.
        
        When removing a location from the itinerary, any PLANNED visits (future visits) at 
        that location on the same date as the itinerary item should also be removed.
        
        If preserve_visits=true query parameter is provided, visits will NOT be deleted.
        This is useful when moving items to global/trip context where we want to keep the visits.
        """
        instance = self.get_object()
        preserve_visits = request.query_params.get('preserve_visits', 'false').lower() == 'true'
        
        # Check if this is a location type itinerary item
        location_ct = ContentType.objects.get_for_model(Location)
        if instance.content_type == location_ct and instance.object_id and not preserve_visits:
            try:
                location = Location.objects.get(id=instance.object_id)
                itinerary_date = instance.date
                
                if itinerary_date:
                    # Convert itinerary date to datetime for comparison
                    if isinstance(itinerary_date, str):
                        itinerary_date = parse_date(itinerary_date)
                    
                    # Find and delete visits at this location on this date
                    # When removing from itinerary, we remove the associated visit
                    visits_to_delete = Visit.objects.filter(
                        location=location,
                        start_date__date=itinerary_date
                    )
                    
                    deleted_count = visits_to_delete.count()
                    if deleted_count > 0:
                        visits_to_delete.delete()
                        
            except Location.DoesNotExist:
                # Location doesn't exist, just proceed with deleting the itinerary item
                pass
        
        # Call parent destroy to delete the itinerary item
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=False, methods=['post'], url_path='reorder')
    @transaction.atomic
    def reorder(self, request):
        """
        Reorder itinerary items in bulk.
        
        Expected payload:
        {
            "items": [
                {"id": "uuid", "date": "2024-01-01", "order": 0},
                {"id": "uuid", "date": "2024-01-01", "order": 1},
                ...
            ]
        }
        """
        items_data = request.data.get('items', [])

        # Delegate to reusable helper which handles validation, permission checks
        # and the two-phase update to avoid unique constraint races.
        updated_items = reorder_itinerary_items(request.user, items_data)

        serializer = self.get_serializer(updated_items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='auto-generate')
    @transaction.atomic
    def auto_generate(self, request):
        """
        Auto-generate itinerary items for a collection based on dated records.
        
        Only works when:
        - Collection has zero itinerary items
        - Collection has dated records (visits, lodging, transportation, notes, checklists)
        
        Expected payload:
        {
            "collection_id": "uuid"
        }
        
        Returns: List of created itinerary items
        """
        collection_id = request.data.get('collection_id')
        
        if not collection_id:
            return Response(
                {"error": "collection_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get collection and check permissions
        try:
            collection = Collection.objects.get(id=collection_id)
        except Collection.DoesNotExist:
            return Response(
                {"error": "Collection not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Permission check: user must be collection owner or in shared_with
        if not (collection.user == request.user or collection.shared_with.filter(id=request.user.id).exists()):
            return Response(
                {"error": "You do not have permission to modify this collection"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            created_items = auto_generate_itinerary(collection)
            serializer = self.get_serializer(created_items, many=True)
            return Response({
                "message": f"Successfully generated {len(created_items)} itinerary items",
                "items": serializer.data
            }, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)


class ItineraryDayViewSet(viewsets.ModelViewSet):
    """ViewSet for managing itinerary day metadata (names and descriptions)"""
    serializer_class = CollectionItineraryDaySerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess]

    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return CollectionItineraryDay.objects.none()
        
        # Return day metadata from collections the user owns or is shared with
        return CollectionItineraryDay.objects.filter(
            Q(collection__user=user) | Q(collection__shared_with=user)
        ).distinct().select_related('collection', 'collection__user').order_by('date')

    def perform_create(self, serializer):
        """Ensure the user has permission to modify the collection"""
        collection = serializer.validated_data.get('collection')
        
        if not collection:
            raise ValidationError("Collection is required")
        
        # Check if user has permission to modify this collection
        if not (collection.user == self.request.user or 
                collection.shared_with.filter(id=self.request.user.id).exists()):
            raise PermissionDenied("You do not have permission to modify this collection")
        
        serializer.save()

    def perform_update(self, serializer):
        """Ensure the user has permission to modify the collection"""
        instance = self.get_object()
        collection = instance.collection
        
        # Check if user has permission to modify this collection
        if not (collection.user == self.request.user or 
                collection.shared_with.filter(id=self.request.user.id).exists()):
            raise PermissionDenied("You do not have permission to modify this collection")
        
        serializer.save()

    def perform_destroy(self, instance):
        """Ensure the user has permission to modify the collection"""
        collection = instance.collection
        
        # Check if user has permission to modify this collection
        if not (collection.user == self.request.user or 
                collection.shared_with.filter(id=self.request.user.id).exists()):
            raise PermissionDenied("You do not have permission to modify this collection")
        
        instance.delete()