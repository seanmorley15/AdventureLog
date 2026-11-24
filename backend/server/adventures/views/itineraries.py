"""
The day plan of a trip, under ``/api/collections/{collection_id}/``.

- ``itinerary-items/``: placements of records on days, the trip-wide list, or Ideas.
- ``days/``: the numbered days.
- ``itinerary/``: the whole plan, and changes that touch all of it (reorder, length, shift).

The rules live in ``adventures.services.day_plan``; these views only translate HTTP.
"""

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, models, transaction
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response

from adventures.access.audience import is_member
from adventures.models import (
    Activity,
    Checklist,
    CollectionActivity,
    CollectionItineraryDay,
    CollectionItineraryItem,
    Location,
    Lodging,
    Note,
    Transportation,
    Visit,
)
from adventures.permissions import IsOwnerOrSharedWithFullAccess
from adventures.serializers import (
    CollectionItineraryDaySerializer,
    CollectionItineraryItemSerializer,
    VisitSerializer,
    plan_state,
    serialize_updated_object,
)
from adventures.serializers.day_plan import (
    AutoGenerateResultSerializer,
    DayDeleteQuerySerializer,
    DayInsertSerializer,
    DayMoveSerializer,
    DurationSerializer,
    ItemDeleteQuerySerializer,
    ItineraryItemCreateSerializer,
    ItineraryItemResultSerializer,
    ItineraryItemUpdateSerializer,
    LogDayResultSerializer,
    LogItemResultSerializer,
    LogVisitSerializer,
    PlanByDaysSerializer,
    PlanStateSerializer,
    PlanStateWithDaySerializer,
    ReorderResultSerializer,
    ReorderSerializer,
    ShiftSerializer,
)
from adventures.services import day_plan
from adventures.services.activity_log import record_activity
from adventures.services.day_plan.files import location_stops_on_day, serialize_day_files
from adventures.services.day_plan.legacy import auto_generate_itinerary, reorder_itinerary_items
from adventures.views.mixins import COLLECTION_ID_PARAMETER, CollectionScopedMixin
from core.exceptions import APIError
from core.serializers import validated

CONTENT_MODELS = {
    'location': Location,
    'transportation': Transportation,
    'note': Note,
    'lodging': Lodging,
    'visit': Visit,
    'checklist': Checklist,
}

ORDER_CONFLICT_MESSAGE = 'The itinerary changed while you were editing. Refresh and try again.'
DAY_PATH_PARAMETER = OpenApiParameter('id', str, OpenApiParameter.PATH, description='The day id (UUID).')


def _record_item_move(request, item):
    record_activity(
        item.collection,
        request,
        CollectionActivity.Verb.ITEM_MOVED,
        item=str(item.pk),
        name=getattr(item.item, 'name', None),
        kind=item.content_type.model,
        day_index=item.day.index if item.day_id else None,
        is_global=item.is_global,
    )


def _record_anchor_change(request, collection, before):
    collection.refresh_from_db(fields=['start_date'])
    if collection.start_date != before:
        record_activity(
            collection,
            request,
            CollectionActivity.Verb.ANCHOR_CHANGED,
            from_date=before.isoformat() if before else None,
            to_date=collection.start_date.isoformat() if collection.start_date else None,
        )


class _DayPlanViewMixin(CollectionScopedMixin):
    """Shared by the three day plan viewsets."""

    openapi_tags = ['Day plan']

    def handle_exception(self, exc):
        # Two edits that land on the same order slot hit the unique constraint.
        if isinstance(exc, IntegrityError):
            exc = APIError(ORDER_CONFLICT_MESSAGE, code='order_conflict', status=status.HTTP_409_CONFLICT)
        return super().handle_exception(exc)

    def get_readable_collection(self):
        """The collection, for its members and guest-link holders. Anyone else gets a 404."""
        collection = self.get_collection()
        if not is_member(self.request, collection):
            raise NotFound('Collection not found.')
        return collection

    def _state_response(self, collection, extra=None, status_code=status.HTTP_200_OK):
        body = plan_state(collection, self.get_serializer_context())
        if extra:
            body.update(extra)
        return Response(body, status=status_code)


@extend_schema(parameters=[COLLECTION_ID_PARAMETER])
@extend_schema_view(
    list=extend_schema(summary="List a trip's itinerary items", description='Every placement in the plan.'),
    retrieve=extend_schema(summary='Get an itinerary item'),
    destroy=extend_schema(
        summary='Remove an itinerary item',
        description='Removes the placement, not the record. Visits it logged stay unless `confirm_delete_visits`.',
        parameters=[ItemDeleteQuerySerializer],
    ),
)
class ItineraryItemViewSet(_DayPlanViewMixin, viewsets.ModelViewSet):
    """
    Itinerary items place a location, lodging, transportation, note or checklist in a trip's
    plan: on a day (`day_index`), across the trip (`is_global`), or in Ideas (neither).
    Members read the plan; the owner and editors change it.
    """

    serializer_class = CollectionItineraryItemSerializer
    permission_classes = [IsOwnerOrSharedWithFullAccess]
    queryset = CollectionItineraryItem.objects.all()
    pagination_class = None
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return CollectionItineraryItem.objects.none()
        collection = self.get_readable_collection()
        return (
            CollectionItineraryItem.objects.filter(collection=collection)
            .select_related('collection', 'collection__user', 'day', 'content_type')
            .prefetch_related('item')
            .order_by('date', 'order')
        )

    def _resolve_content(self, request, content_type_name, object_id):
        model_class = CONTENT_MODELS[content_type_name]
        content_object = model_class.objects.filter(id=object_id).first()
        if content_object is None:
            raise NotFound(f'{content_type_name} not found.')
        if not IsOwnerOrSharedWithFullAccess().has_object_permission(request, self, content_object):
            raise PermissionDenied('You do not have permission to use this record.')
        return content_object

    @extend_schema(
        request=ItineraryItemCreateSerializer,
        responses={
            201: ItineraryItemResultSerializer,
            200: OpenApiResponse(ItineraryItemResultSerializer, description='The record was already placed there.'),
        },
    )
    def create(self, request, *args, **kwargs):
        """
        Place a record in the plan

        Day-based trips place it on `day_index` (or the day with `date`), across the trip with
        `is_global`, or in Ideas. Placing a lodging or transportation sets its dates from the
        day; placing a location never creates a visit.
        """
        params = validated(ItineraryItemCreateSerializer, request.data)
        collection = self.get_editable_collection()
        content_type_name = params['content_type']
        content_object = self._resolve_content(request, content_type_name, params['object_id'])

        if day_plan.is_day_based(collection):
            return self._create_day_placement(collection, params, content_object, content_type_name)
        return self._create_dated_row(collection, params, content_object)

    @transaction.atomic
    def _create_day_placement(self, collection, params, content_object, content_type_name):
        if content_type_name == 'visit':
            content_object = content_object.location
        content_type = ContentType.objects.get_for_model(type(content_object))

        day = None
        is_global = params.get('is_global', False)
        if params.get('day_index') is None and params.get('date') and not is_global:
            day = CollectionItineraryDay.objects.filter(
                collection=collection, index__isnull=False, date=params['date']
            ).first()
            if day is None:
                raise APIError('That date is not a day of this trip.', code='invalid')
        elif params.get('day_index') is not None:
            day = day_plan.get_day_by_index(collection, params['day_index'])

        item, created = day_plan.place_object(
            collection,
            content_type,
            content_object.id,
            day=day,
            is_global=is_global,
            order=params.get('order'),
            span_end_index=params.get('span_end_index') or None,
            is_optional=params.get('is_optional', False),
            start_time=params.get('start_time'),
            end_time=params.get('end_time'),
            timezone_name=params.get('timezone') or None,
        )
        item = CollectionItineraryItem.objects.select_related('day', 'content_type').get(pk=item.pk)
        response_data = dict(self.get_serializer(item).data)
        content_object.refresh_from_db()
        updated = serialize_updated_object(content_object, self.get_serializer_context())
        if updated is not None:
            response_data['updated_object'] = updated
        return Response(response_data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def _create_dated_row(self, collection, params, content_object):
        """Trips keyed by date (not yet converted to a day plan) place items on a calendar date."""
        is_global = params.get('is_global', False)
        item_date = params.get('date')
        if is_global and item_date:
            raise APIError('A trip-wide item must not have a date.', code='invalid')
        if not is_global and not item_date:
            raise APIError('An item on a day needs a date.', code='invalid')
        if item_date and not is_global:
            if collection.start_date and item_date < collection.start_date:
                raise APIError('That date is before the trip starts.', code='invalid')
            if collection.end_date and item_date > collection.end_date:
                raise APIError('That date is after the trip ends.', code='invalid')

        order = params.get('order') or 0
        bucket = (
            CollectionItineraryItem.objects.filter(collection=collection, is_global=True)
            if is_global else
            CollectionItineraryItem.objects.filter(collection=collection, date=item_date, is_global=False, day__isnull=True)
        )
        existing_max = bucket.aggregate(max_order=models.Max('order'))['max_order']
        if existing_max is not None and order <= existing_max:
            order = existing_max + 1

        serializer = self.get_serializer(data={
            'collection': str(collection.id),
            'content_type': ContentType.objects.get_for_model(type(content_object)).pk,
            'object_id': str(content_object.id),
            'date': item_date,
            'is_global': is_global,
            'order': order,
        })
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    PLACEMENT_FIELDS = ('is_optional', 'start_time', 'end_time', 'timezone')
    MOVE_FIELDS = ('day_index', 'is_global', 'order', 'span_end_index')

    @extend_schema(request=ItineraryItemUpdateSerializer, responses=ItineraryItemResultSerializer)
    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        """
        Move or change an itinerary item

        Sending `day_index`, `is_global`, `order` or `span_end_index` moves it (the other items
        close up). `is_optional`, `start_time`, `end_time` and `timezone` change it in place;
        times on a lodging or transportation also change its dates.
        """
        instance = self.get_object()
        params = validated(ItineraryItemUpdateSerializer, request.data, partial=True)
        if not day_plan.is_day_based(instance.collection):
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        if any(key in params for key in self.MOVE_FIELDS):
            is_global = params.get('is_global', False) if 'is_global' in params else instance.is_global
            if 'day_index' in params:
                day = day_plan.get_day_by_index(instance.collection, params['day_index']) \
                    if params['day_index'] is not None else None
            else:
                day = instance.day if not is_global else None
            if is_global:
                day = None
            day_plan.move_placement(
                instance.collection,
                instance,
                day=day,
                is_global=is_global,
                order=params.get('order'),
                span_end_index=params.get('span_end_index'),
                span_given='span_end_index' in params,
            )
            instance.refresh_from_db()
            _record_item_move(request, instance)

        changes = {key: params[key] for key in self.PLACEMENT_FIELDS if key in params}
        if 'timezone' in changes:
            changes['timezone'] = changes['timezone'] or None
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
            updated = serialize_updated_object(
                type(instance.item).objects.get(pk=instance.object_id), self.get_serializer_context()
            )
            if updated is not None:
                response_data['updated_object'] = updated
        return Response(response_data)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if validated(ItemDeleteQuerySerializer, request.query_params)['confirm_delete_visits'] and instance.logged_visit_id:
            visit = instance.logged_visit
            if IsOwnerOrSharedWithFullAccess().has_object_permission(request, self, visit):
                visit.delete()
        collection = instance.collection
        bucket = (instance.day_id, instance.is_global)
        instance.delete()
        if day_plan.is_day_based(collection):
            day_plan.compact_bucket(collection, *bucket)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request=LogVisitSerializer,
        responses={
            201: OpenApiResponse(LogItemResultSerializer, description='A visit was created.'),
            200: OpenApiResponse(LogItemResultSerializer, description='The stop had already logged its visit.'),
            400: OpenApiResponse(description='`date_required` when the trip has no dates, or invalid input.'),
        },
    )
    @action(detail=True, methods=['post'], url_path='log-visit')
    def log_visit(self, request, *args, **kwargs):
        """
        Log a stop as visited

        Creates one visit to the location for this stop's day, or returns the one it already
        logged.
        """
        item = self.get_object()
        self.get_editable_collection()
        visit, created = day_plan.log_visited(item, validated(LogVisitSerializer, request.data).get('date'))
        item.refresh_from_db()
        return Response({
            'item': self.get_serializer(item).data,
            'visit': VisitSerializer(visit, context=self.get_serializer_context()).data,
            'created': created,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@extend_schema(parameters=[COLLECTION_ID_PARAMETER])
class CollectionDayViewSet(_DayPlanViewMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    The numbered days of a day-based trip. Changes that add, remove or reorder days answer
    with the whole plan, so the planner can redraw without another request.
    """

    serializer_class = CollectionItineraryDaySerializer
    queryset = CollectionItineraryDay.objects.all()
    pagination_class = None

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return CollectionItineraryDay.objects.none()
        return CollectionItineraryDay.objects.filter(collection=self.get_readable_collection()).order_by('index', 'date')

    def list(self, request, *args, **kwargs):
        """List a trip's days"""
        return super().list(request, *args, **kwargs)

    @extend_schema(request=DayInsertSerializer, responses={201: PlanStateWithDaySerializer})
    def create(self, request, collection_id=None):
        """
        Add a day

        Inserts a day at `position` (later days move up by one), or at the end. Answers with
        the plan and the new day's id.
        """
        params = validated(DayInsertSerializer, request.data)
        collection = self.get_editable_collection()
        day = day_plan.insert_day(collection, params.get('position'), params.get('name'), params.get('description'))
        return self._state_response(collection, {'day': str(day.pk)}, status.HTTP_201_CREATED)

    @extend_schema(parameters=[DAY_PATH_PARAMETER], request=CollectionItineraryDaySerializer,
                   responses=CollectionItineraryDaySerializer)
    def partial_update(self, request, collection_id=None, pk=None):
        """
        Rename a day

        Changes `name` and `description`. Use the other actions to move a day.
        """
        collection = self.get_editable_collection()
        day = day_plan.get_day(collection, pk)
        changes = {key: request.data[key] for key in ('name', 'description') if key in request.data}
        serializer = self.get_serializer(day, data=changes, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        parameters=[DAY_PATH_PARAMETER, DayDeleteQuerySerializer],
        responses={200: PlanStateSerializer, 400: OpenApiResponse(
            description='`destination_required` (with `item_count`) when the day has stops and no `destination`.'
        )},
    )
    def destroy(self, request, collection_id=None, pk=None):
        """
        Delete a day

        Later days move down by one. The day's stops go to `destination`. Answers with the
        plan (not 204), like the other day changes.
        """
        params = validated(DayDeleteQuerySerializer, request.query_params)
        collection = self.get_editable_collection()
        day_plan.delete_day(
            collection, pk, destination=params.get('destination'),
            target_day_id=str(params['target_day']) if params.get('target_day') else None,
        )
        return self._state_response(collection)

    @extend_schema(parameters=[DAY_PATH_PARAMETER], request=None, responses={201: PlanStateWithDaySerializer})
    @action(detail=True, methods=['post'])
    def duplicate(self, request, collection_id=None, pk=None):
        """
        Duplicate a day

        Adds a copy of the day and its stops right after it.
        """
        collection = self.get_editable_collection()
        day = day_plan.duplicate_day(collection, pk)
        return self._state_response(collection, {'day': str(day.pk)}, status.HTTP_201_CREATED)

    @extend_schema(parameters=[DAY_PATH_PARAMETER], request=DayMoveSerializer, responses=PlanStateSerializer)
    @action(detail=True, methods=['post'])
    def move(self, request, collection_id=None, pk=None):
        """
        Move a day

        Makes the day number `position`; the days between shift by one.
        """
        position = validated(DayMoveSerializer, request.data)['position']
        collection = self.get_editable_collection()
        day = day_plan.get_day(collection, pk)
        from_index = day.index
        day_plan.move_day(collection, day.pk, position)
        day.refresh_from_db()
        if day.index != from_index:
            record_activity(
                collection, request, CollectionActivity.Verb.DAY_MOVED,
                day=str(day.pk), name=day.name, from_index=from_index, to_index=day.index,
            )
        return self._state_response(collection)

    @extend_schema(parameters=[DAY_PATH_PARAMETER], request=LogVisitSerializer, responses=LogDayResultSerializer)
    @action(detail=True, methods=['post'], url_path='log-visit')
    def log_visit(self, request, collection_id=None, pk=None):
        """
        Log a day as visited

        Logs every non-optional location stop on the day that has no visit yet.
        """
        collection = self.get_editable_collection()
        day = day_plan.get_day(collection, pk)
        logged = day_plan.log_day(collection, day, validated(LogVisitSerializer, request.data).get('date'))
        refreshed = CollectionItineraryItem.objects.filter(pk__in=[i.pk for i in logged]) \
            .select_related('day', 'content_type', 'logged_visit').prefetch_related('item')
        needs_stop = []
        if len(location_stops_on_day(day)) > 1:
            needs_stop = [str(a.pk) for a in Activity.objects.filter(day=day, promoted_activity__isnull=True)]
        context = self.get_serializer_context()
        body = {
            'items': CollectionItineraryItemSerializer(refreshed, many=True, context=context).data,
            'visits': VisitSerializer([i.logged_visit for i in refreshed], many=True, context=context).data,
            'activities_need_stop': needs_stop,
        }
        body.update(serialize_day_files(collection, context))
        return Response(body)


@extend_schema(parameters=[COLLECTION_ID_PARAMETER])
class ItineraryViewSet(_DayPlanViewMixin, viewsets.GenericViewSet):
    """The whole plan of a trip, and changes that touch all of it. Routed as a singleton."""

    serializer_class = PlanStateSerializer

    @extend_schema(responses=PlanStateSerializer)
    def retrieve(self, request, collection_id=None):
        """
        Get the plan

        Items, days, lodging, transportation, and the files on days, as the planner draws them.
        """
        return self._state_response(self.get_readable_collection())

    @extend_schema(
        request=ReorderSerializer,
        responses={200: ReorderResultSerializer, 409: OpenApiResponse(
            description='Someone else changed the plan at the same time (`order_conflict`). Reload and retry.'
        )},
    )
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def reorder(self, request, collection_id=None):
        """
        Reorder items

        Moves many items at once, e.g. after a drag and drop. Lodging and transportation dates
        move with their placements.
        """
        validated(ReorderSerializer, request.data)
        collection = self.get_editable_collection()
        items_data = request.data.get('items') or []
        if not items_data:
            return Response({'items': [], 'updated_objects': []})
        ids = [entry.get('id') for entry in items_data]
        if CollectionItineraryItem.objects.filter(id__in=ids).exclude(collection=collection).exists():
            raise NotFound('One or more items are not in this collection.')

        context = self.get_serializer_context()
        if not day_plan.is_day_based(collection):
            updated = reorder_itinerary_items(request, items_data)
            return Response({
                'items': CollectionItineraryItemSerializer(updated, many=True, context=context).data,
                'updated_objects': [],
            })

        items, updated_objects = day_plan.reorder_day_plan(collection, items_data)
        record_activity(collection, request, CollectionActivity.Verb.ITEM_MOVED, count=len(items))
        refreshed = CollectionItineraryItem.objects.filter(pk__in=[i.pk for i in items]) \
            .select_related('day', 'content_type').prefetch_related('item')
        by_pk = {item.pk: item for item in refreshed}
        return Response({
            'items': CollectionItineraryItemSerializer([by_pk[i.pk] for i in items], many=True, context=context).data,
            'updated_objects': [serialize_updated_object(obj, context) for obj in updated_objects],
        })

    @extend_schema(request=None, responses={201: AutoGenerateResultSerializer})
    @action(detail=False, methods=['post'], url_path='auto-generate')
    @transaction.atomic
    def auto_generate(self, request, collection_id=None):
        """
        Fill the plan from dates

        For trips still keyed by date: places every dated record of the collection on its
        date. Day-based trips answer `400 day_based`.
        """
        collection = self.get_editable_collection()
        if day_plan.is_day_based(collection):
            raise APIError('This trip is planned by days. Place items on days instead.', code='day_based')
        created = auto_generate_itinerary(collection)
        return Response(
            {'items': CollectionItineraryItemSerializer(created, many=True, context=self.get_serializer_context()).data},
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=PlanByDaysSerializer, responses=PlanStateSerializer)
    @action(detail=False, methods=['post'], url_path='plan-by-days')
    def plan_by_days(self, request, collection_id=None):
        """
        Convert to a day plan

        Turns a trip keyed by date into numbered days, keeping every placement.
        """
        params = validated(PlanByDaysSerializer, request.data)
        collection = self.get_editable_collection()
        with transaction.atomic():
            day_plan.plan_by_days(collection, params.get('day_count'))
        return self._state_response(collection)

    @extend_schema(
        request=DurationSerializer,
        responses={200: PlanStateSerializer, 400: OpenApiResponse(
            description='`destination_required` (with `day_indexes`) when removed days have stops.'
        )},
    )
    @action(detail=False, methods=['post'])
    def duration(self, request, collection_id=None):
        """
        Change the trip's length

        Sets the number of days and, optionally, the start date (null makes the trip undated).
        Stops on days that are removed go to `destination`. The end date follows.
        """
        params = validated(DurationSerializer, request.data)
        collection = self.get_editable_collection()
        anchor = params['start_date'] if 'start_date' in params else ...
        if 'end_date' in params:
            effective_anchor = anchor if anchor is not ... else collection.start_date
            expected = day_plan.projected_date(effective_anchor, params['day_count']) if effective_anchor else None
            if params['end_date'] != expected:
                raise APIError(
                    'end_date follows from the start date and the day count. Send day_count instead.', code='invalid'
                )
        before = collection.start_date
        day_plan.set_duration(
            collection,
            params['day_count'],
            anchor=anchor,
            destination=params.get('destination'),
            target_day_id=str(params['target_day']) if params.get('target_day') else None,
            timezone_name=params.get('timezone') or None,
        )
        _record_anchor_change(request, collection, before)
        return self._state_response(collection)

    @extend_schema(request=ShiftSerializer, responses=PlanStateSerializer)
    @action(detail=False, methods=['post'])
    def shift(self, request, collection_id=None):
        """
        Move the trip's dates

        Shifts a dated trip by `days`, or to a new `start_date`. Days, order and times stay;
        visits already logged do not move.
        """
        params = validated(ShiftSerializer, request.data)
        collection = self.get_editable_collection()
        before = collection.start_date
        day_plan.shift_anchor(collection, days=params.get('days'), start_date=params.get('start_date'))
        _record_anchor_change(request, collection, before)
        return self._state_response(collection)

