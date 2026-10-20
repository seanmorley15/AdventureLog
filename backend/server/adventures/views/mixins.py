import uuid

from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from adventures.permissions import IsOwnerOrSharedWithFullAccess, ensure_can_change_collection
from adventures.access.audience import can_edit, member_collections_q


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
        user = self.request.user
        # Owned rows and rows in collections the requester is a member of or holds a
        # guest link to. A row's own is_public opens it only when no collection owns it.
        scope = member_collections_q(self.request, 'collection__')
        if user.is_authenticated:
            scope |= Q(user=user.id)
        if self.action == 'retrieve':
            scope |= Q(is_public=True, collection__isnull=True)
        return self.model.objects.filter(scope).distinct().order_by('-updated_at')

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
        """Return the content object, or an error Response if it is invalid or not accessible."""
        models = self.content_object_models

        if content_type_name not in models:
            return Response({
                "error": f"Invalid content_type. Must be one of: {', '.join(models.keys())}"
            }, status=status.HTTP_400_BAD_REQUEST)

        if self.validate_object_uuid:
            # Reject "undefined" and empty ids from the client before they reach the database.
            if not object_id or object_id == 'undefined':
                return Response({
                    "error": "object_id is required and must be a valid UUID"
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                uuid.UUID(str(object_id))
            except (ValueError, AttributeError):
                return Response({
                    "error": f"Invalid object_id format: {object_id}"
                }, status=status.HTTP_400_BAD_REQUEST)

        model = models[content_type_name]
        try:
            content_object = model.objects.get(id=object_id)
        except (ValueError, model.DoesNotExist):
            return Response({
                "error": f"{content_type_name} not found"
            }, status=status.HTTP_404_NOT_FOUND)

        if not IsOwnerOrSharedWithFullAccess().has_object_permission(self.request, self, content_object):
            return Response({
                "error": "User does not have permission to access this content"
            }, status=status.HTTP_403_FORBIDDEN)

        return content_object
