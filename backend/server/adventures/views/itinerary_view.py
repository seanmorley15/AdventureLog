from adventures.models import Location, Collection, CollectionItineraryItem, Transportation, Note, Lodging, Visit, Checklist, CollectionItineraryDay
from django.utils.dateparse import parse_date, parse_datetime, parse_time
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, models
from adventures.serializers import (
    CollectionItineraryItemSerializer,
    CollectionItineraryDaySerializer,
    LodgingSerializer,
    TransportationSerializer,
    VisitSerializer,
)
from adventures.utils.itinerary import reorder_itinerary_items
from adventures.utils.autogenerate_itinerary import auto_generate_itinerary
from adventures.utils import itinerary_days as day_plan
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from django.db.models import Q
from django.db import transaction

CONTENT_MODELS = {
    'location': Location,
    'transportation': Transportation,
    'note': Note,
    'lodging': Lodging,
    'visit': Visit,
    'checklist': Checklist,
}

_ERROR_STATUS = {
    'not_found': status.HTTP_404_NOT_FOUND,
    'conflict': status.HTTP_409_CONFLICT,
}

ORDER_CONFLICT = {
    'error': 'The itinerary changed while you were editing. Refresh and try again.',
    'code': 'order_conflict',
}


def _plan_error(exc: day_plan.DayPlanError):
    body = {'error': exc.message, 'code': exc.code, **exc.extra}
    return Response(body, status=_ERROR_STATUS.get(exc.code, status.HTTP_400_BAD_REQUEST))


def _parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('1', 'true', 'yes', 'y', 't')


def _parse_day_date(value):
    if value in (None, ''):
        return None
    text = str(value)
    parsed = parse_date(text.split('T')[0])
    if parsed is None:
        raise day_plan.DayPlanError('Use a YYYY-MM-DD date.')
    return parsed


def _parse_clock(value):
    if value in (None, ''):
        return None
    parsed = parse_time(str(value))
    if parsed is None:
        raise day_plan.DayPlanError('Use an HH:MM time.')
    return parsed


def _is_member(user, collection):
    return collection.user_id == user.id or collection.shared_with.filter(id=user.id).exists()


def _member_collection(request, collection_id):
    if not collection_id:
        raise day_plan.DayPlanError('collection is required.')
    try:
        collection = Collection.objects.get(id=collection_id)
    except (Collection.DoesNotExist, ValueError, TypeError):
        raise day_plan.DayPlanError('Collection not found.', code='not_found')
    except Exception:
        raise day_plan.DayPlanError('Collection not found.', code='not_found')
    if not _is_member(request.user, collection):
        raise PermissionDenied('You do not have permission to modify this collection.')
    return collection


def plan_state(collection, context=None):
    """The day plan the planner renders, returned after structural changes."""
    from adventures.utils.day_files import serialize_day_files

    collection.refresh_from_db()
    items = CollectionItineraryItem.objects.filter(collection=collection).select_related('day', 'content_type')
    days = CollectionItineraryDay.objects.filter(collection=collection).order_by('index', 'date')
    context = context or {}
    state = {
        'collection': {
            'id': str(collection.id),
            'start_date': collection.start_date,
            'end_date': collection.end_date,
            'timezone': collection.timezone,
            'day_count': day_plan.day_count(collection) or None,
            'updated_at': collection.updated_at,
        },
        'itinerary': CollectionItineraryItemSerializer(items, many=True, context=context).data,
        'itinerary_days': CollectionItineraryDaySerializer(days, many=True, context=context).data,
        'lodging': LodgingSerializer(collection.lodging_set.all(), many=True, context=context).data,
        'transportations': TransportationSerializer(collection.transportation_set.all(), many=True, context=context).data,
    }
    state.update(serialize_day_files(collection, context))
    return state


def _serialize_updated_object(obj, context):
    if obj is None:
        return None
    if isinstance(obj, Lodging):
        return LodgingSerializer(obj, context=context).data
    if isinstance(obj, Transportation):
        return TransportationSerializer(obj, context=context).data
    return None


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
        ).distinct().select_related('collection', 'collection__user', 'day', 'content_type').order_by('date', 'order')

    def handle_exception(self, exc):
        if isinstance(exc, IntegrityError):
            return Response(ORDER_CONFLICT, status=status.HTTP_409_CONFLICT)
        if isinstance(exc, day_plan.DayPlanError):
            return _plan_error(exc)
        return super().handle_exception(exc)

    def _resolve_content(self, request, content_type_val, object_id):
        if content_type_val not in CONTENT_MODELS:
            raise ValidationError({'error': f"Invalid content_type. Must be one of: {', '.join(CONTENT_MODELS)}"})
        model_class = CONTENT_MODELS[content_type_val]
        try:
            content_object = model_class.objects.get(id=object_id)
        except (ValueError, model_class.DoesNotExist):
            return None, None
        except Exception:
            return None, None
        permission_checker = IsOwnerOrSharedWithFullAccess()
        if not permission_checker.has_object_permission(request, self, content_object):
            raise PermissionDenied('User does not have permission to access this content')
        return content_object, ContentType.objects.get_for_model(model_class)

    def create(self, request, *args, **kwargs):
        """
        Accept 'content_type' as either a ContentType PK or a model name string
        (e.g. 'location', 'lodging', 'transportation', 'note', 'visit').

        Day-based trips place the object on ``day_index`` (or in Ideas when it is
        omitted, or trip-wide with ``is_global``). Lodging and transport dates are
        written with the placement. ``update_item_date`` is ignored: placing a
        location never creates or rewrites a visit.
        """
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data.copy()
        content_type_val = data.get('content_type')
        object_id = data.get('object_id')
        is_global = _parse_bool(data.get('is_global'), False)
        data['is_global'] = is_global
        if is_global and not data.get('date'):
            data['date'] = None

        # Support legacy field 'location' -> treat as content_type='location'
        if not content_type_val and data.get('location'):
            content_type_val = 'location'
            object_id = object_id or data.get('location')
            data['content_type'] = content_type_val
            data['object_id'] = object_id

        content_object = None
        if content_type_val and isinstance(content_type_val, str) and not content_type_val.isdigit():
            content_object, ct = self._resolve_content(request, content_type_val, object_id)
            if content_object is None:
                return Response({'error': f"{content_type_val} not found"}, status=status.HTTP_404_NOT_FOUND)
            data['content_type'] = ct.pk

        collection_id = data.get('collection')
        collection = None
        if collection_id:
            try:
                collection = Collection.objects.get(id=collection_id)
            except (Collection.DoesNotExist, ValueError):
                return Response({'error': 'Collection not found'}, status=status.HTTP_404_NOT_FOUND)
            except Exception:
                return Response({'error': 'Collection not found'}, status=status.HTTP_404_NOT_FOUND)

        if collection is not None and day_plan.is_day_based(collection):
            return self._create_day_placement(request, collection, data, content_object, content_type_val)

        return self._create_dated_row(request, data, collection, is_global)

    @transaction.atomic
    def _create_day_placement(self, request, collection, data, content_object, content_type_val):
        if not _is_member(request.user, collection):
            raise PermissionDenied('You do not have permission to modify this collection.')
        if content_object is None:
            content_type = ContentType.objects.filter(pk=data.get('content_type')).first()
            if content_type is None:
                return Response({'error': 'content_type is required'}, status=status.HTTP_400_BAD_REQUEST)
            content_type_val = content_type.model
            content_object, _ = self._resolve_content(request, content_type_val, data.get('object_id'))
            if content_object is None:
                return Response({'error': f"{content_type_val} not found"}, status=status.HTTP_404_NOT_FOUND)
        if content_type_val == 'visit':
            content_object = content_object.location
            content_type_val = 'location'
        content_type = ContentType.objects.get_for_model(type(content_object))

        day = None
        day_index = data.get('day_index')
        if day_index in (None, '') and data.get('date') and not data.get('is_global'):
            target = _parse_day_date(data.get('date'))
            day = CollectionItineraryDay.objects.filter(collection=collection, index__isnull=False, date=target).first()
            if day is None:
                return Response({'error': 'That date is not a day of this trip.'}, status=status.HTTP_400_BAD_REQUEST)
        elif day_index not in (None, ''):
            day = day_plan.get_day_by_index(collection, day_index)

        order = data.get('order')
        item, created = day_plan.place_object(
            collection,
            content_type,
            content_object.id,
            day=day,
            is_global=bool(data.get('is_global')),
            order=int(order) if order not in (None, '') else None,
            span_end_index=data.get('span_end_index') or None,
            is_optional=_parse_bool(data.get('is_optional'), False),
            start_time=_parse_clock(data.get('start_time')),
            end_time=_parse_clock(data.get('end_time')),
            timezone_name=data.get('timezone') or None,
        )
        item = CollectionItineraryItem.objects.select_related('day', 'content_type').get(pk=item.pk)
        context = self.get_serializer_context()
        response_data = dict(self.get_serializer(item).data)
        content_object.refresh_from_db()
        updated = _serialize_updated_object(content_object, context)
        if updated is not None:
            response_data['updated_object'] = updated
        return Response(response_data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def _create_dated_row(self, request, data, collection, is_global):
        item_date = data.get('date')
        item_order = data.get('order', 0)

        if is_global and item_date:
            return Response({'error': 'Global itinerary items must not include a date.'}, status=status.HTTP_400_BAD_REQUEST)
        if (not is_global) and not item_date:
            return Response({'error': 'Dated itinerary items must include a date.'}, status=status.HTTP_400_BAD_REQUEST)

        # The itinerary date must fall inside the collection's date range.
        if collection is not None and item_date and not is_global:
            parsed_date = parse_date(str(item_date))
            if parsed_date is None:
                dt = parse_datetime(str(item_date))
                parsed_date = dt.date() if dt else None
            if parsed_date is not None:
                if collection.start_date and parsed_date < collection.start_date:
                    return Response({'error': 'Itinerary item date is before the collection start_date'}, status=status.HTTP_400_BAD_REQUEST)
                if collection.end_date and parsed_date > collection.end_date:
                    return Response({'error': 'Itinerary item date is after the collection end_date'}, status=status.HTTP_400_BAD_REQUEST)

        if collection is not None:
            if is_global:
                existing_max = CollectionItineraryItem.objects.filter(
                    collection=collection, is_global=True
                ).aggregate(max_order=models.Max('order'))['max_order']
                if existing_max is None:
                    existing_max = -1
                if item_order is None or int(item_order) <= existing_max:
                    data['order'] = existing_max + 1
            elif item_date:
                existing_max = CollectionItineraryItem.objects.filter(
                    collection=collection, date=item_date, is_global=False, day__isnull=True
                ).aggregate(max_order=models.Max('order'))['max_order']
                if existing_max is not None and int(item_order or 0) <= existing_max:
                    data['order'] = existing_max + 1

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    PLACEMENT_FIELDS = ('is_optional', 'start_time', 'end_time', 'timezone')

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not day_plan.is_day_based(instance.collection):
            return super().update(request, *args, **kwargs)

        data = request.data
        moving = any(key in data for key in ('day_index', 'is_global', 'order', 'span_end_index'))
        if moving:
            is_global = _parse_bool(data.get('is_global'), instance.is_global if 'is_global' not in data else False)
            if 'day_index' in data:
                day = day_plan.get_day_by_index(instance.collection, data['day_index']) if data['day_index'] not in (None, '') else None
            else:
                day = instance.day if not is_global else None
            if is_global:
                day = None
            order = data.get('order')
            day_plan.move_placement(
                instance.collection,
                instance,
                day=day,
                is_global=is_global,
                order=int(order) if order not in (None, '') else None,
                span_end_index=data.get('span_end_index') if 'span_end_index' in data else None,
                span_given='span_end_index' in data,
            )
            instance.refresh_from_db()

        changes = {}
        for key in self.PLACEMENT_FIELDS:
            if key not in data:
                continue
            value = data.get(key)
            if key == 'is_optional':
                value = _parse_bool(value)
            elif key in ('start_time', 'end_time'):
                value = _parse_clock(value)
            else:
                value = value or None
            changes[key] = value
        if changes:
            serializer = self.get_serializer(instance, data=changes, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            instance.refresh_from_db()
            if instance.day_id and ('start_time' in changes or 'end_time' in changes):
                day_plan.write_object_dates(instance, instance.collection.start_date)

        instance = CollectionItineraryItem.objects.select_related('day', 'content_type').get(pk=instance.pk)
        response_data = dict(self.get_serializer(instance).data)
        if instance.item is not None:
            updated = _serialize_updated_object(type(instance.item).objects.get(pk=instance.object_id), self.get_serializer_context())
            if updated is not None:
                response_data['updated_object'] = updated
        return Response(response_data)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """
        Remove a placement. Visits are kept: placing never created them, so
        removing never deletes them. ``confirm_delete_visits=true`` deletes the
        visit this placement logged. ``preserve_visits`` is accepted and keeps
        visits, as it always did.
        """
        instance = self.get_object()
        confirm_delete = _parse_bool(request.query_params.get('confirm_delete_visits'), False)
        if confirm_delete and instance.logged_visit_id:
            visit = instance.logged_visit
            if IsOwnerOrSharedWithFullAccess().has_object_permission(request, self, visit):
                visit.delete()
        collection = instance.collection
        bucket = (instance.day_id, instance.is_global)
        instance.delete()
        if day_plan.is_day_based(collection):
            day_plan._compact_bucket(collection, *bucket)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['post'], url_path='reorder')
    @transaction.atomic
    def reorder(self, request):
        """
        Reorder itinerary items in bulk.

        Date-keyed trips: ``{"items": [{"id", "date", "order", "is_global"}]}``.
        Day-based trips: ``{"items": [{"id", "day_index", "order", "is_global", "span_end_index"?}]}``.
        Lodging and transport dates move with their placement. A unique-order
        conflict returns 409; refetch and retry.
        """
        items_data = request.data.get('items', [])
        if not items_data:
            return Response([], status=status.HTTP_200_OK)

        first = CollectionItineraryItem.objects.filter(id=items_data[0].get('id')).select_related('collection').first()
        if first is not None and day_plan.is_day_based(first.collection):
            if not _is_member(request.user, first.collection):
                raise PermissionDenied('You do not have permission to modify this collection.')
            items, updated_objects = day_plan.reorder_day_plan(first.collection, items_data)
            refreshed = CollectionItineraryItem.objects.filter(pk__in=[i.pk for i in items]).select_related('day', 'content_type')
            by_pk = {item.pk: item for item in refreshed}
            context = self.get_serializer_context()
            return Response({
                'items': self.get_serializer([by_pk[i.pk] for i in items], many=True).data,
                'updated_objects': [_serialize_updated_object(obj, context) for obj in updated_objects],
            }, status=status.HTTP_200_OK)

        # Delegate to reusable helper which handles validation, permission checks
        # and the two-phase update to avoid unique constraint races.
        updated_items = reorder_itinerary_items(request.user, items_data)

        serializer = self.get_serializer(updated_items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='auto-generate')
    @transaction.atomic
    def auto_generate(self, request):
        """
        Auto-generate itinerary items for a date-keyed collection from dated records.

        Day-based trips are built by the conversion and do not use this.
        """
        collection_id = request.data.get('collection_id')
        
        if not collection_id:
            return Response(
                {"error": "collection_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            collection = Collection.objects.get(id=collection_id)
        except Collection.DoesNotExist:
            return Response(
                {"error": "Collection not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not _is_member(request.user, collection):
            return Response(
                {"error": "You do not have permission to modify this collection"},
                status=status.HTTP_403_FORBIDDEN
            )
        if day_plan.is_day_based(collection):
            return Response(
                {"error": "This trip is planned by days. Place items on days instead."},
                status=status.HTTP_400_BAD_REQUEST,
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

    # -- Day plan actions ---------------------------------------------------

    def _state_response(self, collection, extra=None, status_code=status.HTTP_200_OK):
        body = plan_state(collection, self.get_serializer_context())
        if extra:
            body.update(extra)
        return Response(body, status=status_code)

    @action(detail=False, methods=['post'], url_path='plan-by-days')
    def plan_by_days(self, request):
        """Build a day plan for a date-keyed trip. Omit ``day_count`` to use the date span."""
        collection = _member_collection(request, request.data.get('collection'))
        raw_count = request.data.get('day_count', None)
        if raw_count in (None, ''):
            count = None
        else:
            try:
                count = int(raw_count)
            except (TypeError, ValueError):
                raise day_plan.DayPlanError('Day count must be a whole number.')
        with transaction.atomic():
            day_plan.plan_by_days(collection, count)
        return self._state_response(collection)

    @action(detail=False, methods=['post'], url_path='days/insert')
    def insert_day(self, request):
        collection = _member_collection(request, request.data.get('collection'))
        position = request.data.get('position')
        day = day_plan.insert_day(
            collection,
            int(position) if position not in (None, '') else None,
            request.data.get('name'),
            request.data.get('description'),
        )
        return self._state_response(collection, {'day': str(day.pk)}, status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='days/duplicate')
    def duplicate_day(self, request):
        collection = _member_collection(request, request.data.get('collection'))
        day = day_plan.duplicate_day(collection, request.data.get('day'))
        return self._state_response(collection, {'day': str(day.pk)}, status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='days/move')
    def move_day(self, request):
        collection = _member_collection(request, request.data.get('collection'))
        position = request.data.get('position')
        if position in (None, ''):
            raise day_plan.DayPlanError('position is required.')
        day_plan.move_day(collection, request.data.get('day'), int(position))
        return self._state_response(collection)

    @action(detail=False, methods=['post'], url_path='days/delete')
    def delete_day(self, request):
        collection = _member_collection(request, request.data.get('collection'))
        day_plan.delete_day(
            collection,
            request.data.get('day'),
            destination=request.data.get('destination'),
            target_day_id=request.data.get('target_day'),
        )
        return self._state_response(collection)

    @action(detail=False, methods=['post'], url_path='duration')
    def duration(self, request):
        """
        Set the day count and, optionally, the anchor (``start_date``; null clears it).
        ``end_date`` is derived; sending one that does not match returns 400.
        """
        collection = _member_collection(request, request.data.get('collection'))
        count = request.data.get('day_count')
        if count in (None, ''):
            raise day_plan.DayPlanError('day_count is required.')
        anchor = ...
        if 'start_date' in request.data:
            anchor = _parse_day_date(request.data.get('start_date'))
        if 'end_date' in request.data:
            effective_anchor = anchor if anchor is not ... else collection.start_date
            expected = day_plan.projected_date(effective_anchor, int(count)) if effective_anchor else None
            if _parse_day_date(request.data.get('end_date')) != expected:
                raise day_plan.DayPlanError(
                    'end_date is derived from the start date and the day count. Send day_count instead.'
                )
        day_plan.set_duration(
            collection,
            count,
            anchor=anchor,
            destination=request.data.get('destination'),
            target_day_id=request.data.get('target_day'),
            timezone_name=request.data.get('timezone') or None,
        )
        return self._state_response(collection)

    @action(detail=False, methods=['post'], url_path='shift')
    def shift(self, request):
        """
        Shift an anchored trip by ``days`` (civil days, may be negative) or to a new
        ``start_date``. Indexes, order, and clock faces stay; visits do not move.
        """
        collection = _member_collection(request, request.data.get('collection'))
        start_date = _parse_day_date(request.data.get('start_date'))
        days = request.data.get('days')
        if start_date is None and days in (None, ''):
            raise day_plan.DayPlanError('Send days or start_date.')
        day_plan.shift_anchor(collection, days=days, start_date=start_date)
        return self._state_response(collection)

    @action(detail=True, methods=['post'], url_path='log-visited')
    def log_visited(self, request, pk=None):
        """Create one visit for this stop, or return the visit it already logged."""
        item = self.get_object()
        if not _is_member(request.user, item.collection):
            raise PermissionDenied('You do not have permission to modify this collection.')
        visit_date = _parse_day_date(request.data.get('date'))
        visit, created = day_plan.log_visited(item, visit_date)
        item.refresh_from_db()
        return Response({
            'item': self.get_serializer(item).data,
            'visit': VisitSerializer(visit, context=self.get_serializer_context()).data,
            'created': created,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='log-day')
    def log_day(self, request):
        """Log every non-optional location stop on a day that has no logged visit."""
        collection = _member_collection(request, request.data.get('collection'))
        day = day_plan._get_day(collection, request.data.get('day'))
        visit_date = _parse_day_date(request.data.get('date'))
        logged = day_plan.log_day(collection, day, visit_date)
        refreshed = CollectionItineraryItem.objects.filter(pk__in=[i.pk for i in logged]).select_related('day', 'content_type', 'logged_visit')
        from adventures.models import Activity
        from adventures.utils.day_files import location_stops_on_day, serialize_day_files

        needs_stop = []
        if len(location_stops_on_day(day)) > 1:
            needs_stop = [
                str(activity.pk)
                for activity in Activity.objects.filter(day=day, promoted_activity__isnull=True)
            ]
        body = {
            'items': self.get_serializer(refreshed, many=True).data,
            'visits': VisitSerializer([i.logged_visit for i in refreshed], many=True, context=self.get_serializer_context()).data,
            'activities_need_stop': needs_stop,
        }
        body.update(serialize_day_files(collection, self.get_serializer_context()))
        return Response(body, status=status.HTTP_200_OK)


class ItineraryDayViewSet(viewsets.ModelViewSet):
    """Day names and descriptions. Day-based trips add and remove days with the itinerary actions."""
    serializer_class = CollectionItineraryDaySerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess]

    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return CollectionItineraryDay.objects.none()
        
        # Return day metadata from collections the user owns or is shared with
        return CollectionItineraryDay.objects.filter(
            Q(collection__user=user) | Q(collection__shared_with=user)
        ).distinct().select_related('collection', 'collection__user').order_by('index', 'date')

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
        if instance.index is not None:
            raise ValidationError("Delete a trip day with the itinerary day actions.")
        
        instance.delete()
