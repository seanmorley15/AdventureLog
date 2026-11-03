import uuid

from django.db.models import Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.exceptions import NotAuthenticated, NotFound, PermissionDenied
from rest_framework.response import Response

from adventures.models import Collection
from adventures.permissions import IsOwnerOrSharedWithFullAccess, ensure_can_change_collection
from adventures.access.audience import audience_for_request, can_edit, member_collections_q
from core.exceptions import APIError
from core.serializers import validated


class CollectionFilterSerializer(serializers.Serializer):
    collection = serializers.UUIDField(
        required=False, help_text='Only records in this collection (yours or one shared with you).'
    )


COLLECTION_ID_PARAMETER = OpenApiParameter(
    'collection_id', OpenApiTypes.UUID, OpenApiParameter.PATH, description='The collection id.'
)


class CollectionScopedMixin:
    """
    For viewsets nested under ``/api/collections/{collection_id}/``.

    ``get_collection()`` loads the collection named in the path once per request. An id that
    is not a UUID or names no collection is a 404; who may read or change it is decided by
    the viewset, with the ``adventures.access.audience`` helpers.
    """

    def get_collection(self):
        if not hasattr(self, '_collection'):
            try:
                collection_id = uuid.UUID(str(self.kwargs.get('collection_id')))
            except ValueError:
                raise NotFound('Collection not found.')
            collection = Collection.objects.select_related('user').filter(pk=collection_id).first()
            if collection is None:
                raise NotFound('Collection not found.')
            self._collection = collection
        return self._collection

    def get_editable_collection(self):
        """
        The collection, when the requester is its owner, an editor, or holds an editor guest link.

        Someone who cannot see the collection at all gets a 404; a viewer gets a 403.
        """
        collection = self.get_collection()
        if not can_edit(self.request, collection):
            if audience_for_request(self.request, collection) is None:
                raise NotFound('Collection not found.')
            raise PermissionDenied('You do not have permission to change this collection.')
        return collection


class CollectionOwnedViewSetMixin:
    """
    Shared behavior of the records that live in a collection or stand alone: lodging,
    transportation, notes, and checklists.

    Set ``model`` on the viewset. Who can see and change a record follows the
    collection's audience (see ``adventures.access.audience``).
    """

    permission_classes = [IsOwnerOrSharedWithFullAccess]
    model = None

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.model.objects.none()
        user = self.request.user
        # Owned rows and rows in collections the requester is a member of or holds a
        # guest link to. A row's own is_public opens it only when no collection owns it.
        scope = member_collections_q(self.request, 'collection__')
        if user.is_authenticated:
            scope |= Q(user=user.id)
        if self.action == 'retrieve':
            scope |= Q(is_public=True, collection__isnull=True)
        return self.model.objects.filter(scope).distinct().order_by('-updated_at')

    @extend_schema(parameters=[CollectionFilterSerializer])
    def list(self, request, *args, **kwargs):
        """
        List your records of this kind, newest change first. With `collection`, list the ones
        in that collection instead, including records other members added.
        """
        collection_id = validated(CollectionFilterSerializer, request.query_params).get('collection')
        if collection_id:
            queryset = self.get_queryset().filter(collection_id=collection_id)
        elif request.user.is_authenticated:
            queryset = self.model.objects.filter(user=request.user).order_by('-updated_at')
        else:
            raise NotAuthenticated()
        return Response(self.get_serializer(self.optimize_list(queryset), many=True).data)

    def optimize_list(self, queryset):
        """Load what the list serializer reads. Override per resource."""
        return queryset

    def perform_create(self, serializer):
        collection = serializer.validated_data.get('collection')

        if collection:
            # Owner, editor, or guest editor. Viewers cannot add records.
            if not can_edit(self.request, collection):
                raise PermissionDenied("You do not have permission to use this collection.")
            # A record in a collection belongs to the collection's owner.
            serializer.save(user=collection.user)
            return

        if not self.request.user.is_authenticated:
            raise PermissionDenied("A guest link can only add records to its collection.")
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        ensure_can_change_collection(self.request, serializer.instance, serializer.validated_data)
        serializer.save()


class PaginatedResponseMixin:
    """``paginate_and_respond`` for list-style actions that build their own queryset."""

    def paginate_and_respond(self, queryset, request, serializer_class=None):
        """Paginate queryset and return response."""
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer_cls = serializer_class or self.get_serializer_class()
        context = self.get_serializer_context()

        if page is not None:
            serializer = serializer_cls(page, many=True, context=context)
            return paginator.get_paginated_response(serializer.data)

        serializer = serializer_cls(queryset, many=True, context=context)
        return Response(serializer.data)


class ContentObjectMixin:
    """
    Resolve the record a generic-relation upload (image, attachment) is attached to.

    Set ``content_object_models`` to the ``{content_type name: model}`` the viewset accepts.
    Set ``validate_object_uuid`` when ``object_id`` should be rejected unless it is a UUID.
    """

    content_object_models = {}
    validate_object_uuid = False

    def _get_and_validate_content_object(self, content_type_name, object_id):
        """The record an upload is attached to. Raises a 400, 403 or 404 when it cannot be used."""
        models = self.content_object_models

        if content_type_name not in models:
            raise APIError(f"content_type must be one of: {', '.join(models.keys())}.", code='invalid')

        if self.validate_object_uuid:
            try:
                uuid.UUID(str(object_id))
            except (ValueError, AttributeError):
                raise APIError('object_id must be a UUID.', code='invalid')

        model = models[content_type_name]
        try:
            content_object = model.objects.get(id=object_id)
        except (ValueError, model.DoesNotExist):
            raise NotFound(f'{content_type_name} not found.')

        if not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, content_object):
            raise PermissionDenied('You do not have permission to change this record.')

        return content_object
