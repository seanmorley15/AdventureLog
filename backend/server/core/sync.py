"""
What a client needs to write safely while it may have been offline.

``ConditionalWritesMixin`` gives a viewset's records an ``ETag`` and lets a client say
``If-Match: <etag>`` on a change or a delete, so a write made from an old copy is refused
(``412 precondition_failed``, with the current record) instead of overwriting a newer one.
``ClientIdsMixin`` lets a client choose the id of the record it creates, so retrying a create whose
answer was lost returns the record that already exists instead of making a second one.

Both are opt-in per request: a client that sends no ``If-Match`` and no ``id`` (the web app) is
unaffected. The record needs an ``updated_at`` that its serializer returns.
"""

from datetime import datetime, timedelta, timezone

from django.db import IntegrityError, transaction
from django.utils.dateparse import parse_datetime
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from core.exceptions import APIError

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_CHANGING_METHODS = {'PUT', 'PATCH', 'DELETE'}
# Actions whose response is one record.
_ETAG_ACTIONS = {'retrieve', 'create', 'update', 'partial_update'}


def etag_for_time(updated_at):
    """The entity tag for a record last changed at ``updated_at``: its microseconds since 1970, quoted."""
    return f'"{(updated_at - _EPOCH) // timedelta(microseconds=1)}"'


def etag_for(instance):
    return etag_for_time(instance.updated_at)


def if_match_allows(header, current_etag):
    """
    Whether an ``If-Match`` header permits a change to a record whose tag is ``current_etag``.

    The header is a comma-separated list of tags, or ``*`` for "any existing record". Tags are
    compared strongly, so a weak tag (``W/"…"``) never matches.
    """
    tags = [tag.strip() for tag in header.split(',') if tag.strip()]
    return '*' in tags or current_etag in tags


def _updated_at_of(data):
    value = data.get('updated_at') if hasattr(data, 'get') else None
    return parse_datetime(value) if isinstance(value, str) else None


class ConditionalWritesMixin:
    """
    ``ETag`` on single-record responses, and ``If-Match`` on changes and deletes.

    A request with ``If-Match`` runs in one transaction that locks the record while it is compared
    and changed, so two such writers cannot both succeed from the same version. Put this mixin
    before the viewset's other bases.
    """

    def dispatch(self, request, *args, **kwargs):
        if request.method not in _CHANGING_METHODS or 'If-Match' not in request.headers:
            return super().dispatch(request, *args, **kwargs)
        with transaction.atomic():
            response = super().dispatch(request, *args, **kwargs)
            if response.status_code >= 400:
                # Nothing a refused request started may be kept.
                transaction.set_rollback(True)
            return response

    def get_object(self):
        instance = super().get_object()
        header = self.request.headers.get('If-Match')
        if header is None or self.request.method not in _CHANGING_METHODS:
            return instance
        # Lock the row, then read it again: another writer may have committed since it was fetched.
        locked = type(instance)._default_manager.select_for_update().filter(pk=instance.pk).first()
        if locked is None:
            raise NotFound()
        instance.refresh_from_db()
        if not if_match_allows(header, etag_for(instance)):
            raise APIError(
                'This record has changed since you last read it.',
                code='precondition_failed',
                status=status.HTTP_412_PRECONDITION_FAILED,
                current=self.get_serializer(instance).data,
            )
        return instance

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        data = getattr(response, 'data', None)
        if response.status_code in (200, 201) and getattr(self, 'action', None) in _ETAG_ACTIONS:
            updated_at = _updated_at_of(data)
        elif response.status_code == 412:
            updated_at = _updated_at_of(data.get('current')) if hasattr(data, 'get') else None
        else:
            updated_at = None
        if updated_at is not None:
            response['ETag'] = etag_for_time(updated_at)
        return response


class ClientIdsMixin:
    """
    ``POST`` accepts an optional ``id`` (a UUID) for the new record.

    - A record with that id that the requester can already see is returned with ``200``, as it is
      stored, without validating or applying the request again. This makes a retry safe.
    - An id used by a record the requester cannot see is a ``409 conflict``.
    - Anything else creates the record with that id.
    """

    def create(self, request, *args, **kwargs):
        raw = request.data.get('id') if hasattr(request.data, 'get') else None
        if raw in (None, ''):
            return super().create(request, *args, **kwargs)
        try:
            client_id = serializers.UUIDField().to_internal_value(raw)
        except serializers.ValidationError as error:
            raise serializers.ValidationError({'id': error.detail})

        existing = self._visible_record(client_id)
        if existing is not None:
            return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # ``id`` is read-only on the serializers, so it is added to what ``save()`` creates with.
        serializer.validated_data['id'] = client_id
        try:
            with transaction.atomic():
                self.perform_create(serializer)
        except IntegrityError:
            # Two retries at once: the other one won. Answer with its record.
            existing = self._visible_record(client_id)
            if existing is None:
                raise
            return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def _visible_record(self, pk):
        return self.get_queryset().filter(pk=pk).first()
