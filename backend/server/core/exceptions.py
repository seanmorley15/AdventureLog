"""
One error body for the whole API.

Every error response is ``{"detail": str, "code": str}``. Validation errors add ``fields``
with the messages for each input, and some errors add documented context keys (a quota,
a partial result). ``api_exception_handler`` is DRF's ``EXCEPTION_HANDLER``.
"""

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.db import IntegrityError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.views import exception_handler as drf_exception_handler

from core.errors import ServiceError


class APIError(exceptions.APIException):
    """
    An error a view raises with its own status and code.

        raise APIError('Collection not found.', code='not_found', status=404)

    Keyword arguments beyond these become extra keys in the body.
    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'invalid'

    def __init__(self, detail, code=None, status=None, **extra):
        super().__init__(detail, code or self.default_code)
        if status is not None:
            self.status_code = status
        self.extra = extra


def _first_message(errors):
    """The first message in a (possibly nested) DRF error structure, with the field it belongs to."""
    if isinstance(errors, dict):
        for key, value in errors.items():
            field, message = _first_message(value)
            if message is not None:
                return (field or key), message
    elif isinstance(errors, (list, tuple)):
        for value in errors:
            field, message = _first_message(value)
            if message is not None:
                return field, message
    elif errors is not None:
        return None, str(errors)
    return None, None


def _validation_body(data):
    fields = data if isinstance(data, dict) else {'non_field_errors': data}
    # Every field maps to a list of messages, also when a view raised {'field': 'message'}.
    fields = {key: [value] if isinstance(value, str) else value for key, value in fields.items()}
    field, message = _first_message(fields)
    if message is None:
        detail = 'Invalid input.'
    elif field and field != 'non_field_errors':
        detail = f'{field}: {message}'
    else:
        detail = message
    return {'detail': detail, 'code': 'validation_error', 'fields': fields}


def _code_for(exc):
    codes = exc.get_codes()
    if isinstance(codes, str):
        return codes
    if isinstance(codes, dict) and isinstance(codes.get('detail'), str):
        return codes['detail']
    return exc.default_code


def to_api_exception(exc):
    """Translate service, Django, and database errors into DRF exceptions; others pass through."""
    if isinstance(exc, ServiceError):
        return APIError(exc.message, code=exc.code, status=exc.status, **exc.extra)
    if isinstance(exc, Http404):
        return exceptions.NotFound()
    if isinstance(exc, DjangoPermissionDenied):
        return exceptions.PermissionDenied(str(exc) or None)
    if isinstance(exc, IntegrityError):
        return APIError(
            'The request conflicts with the current state of the data. Refresh and try again.',
            code='conflict',
            status=status.HTTP_409_CONFLICT,
        )
    return exc


def api_exception_handler(exc, context):
    exc = to_api_exception(exc)
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, exceptions.ValidationError):
        response.data = _validation_body(response.data)
        return response

    data = response.data
    detail = data.get('detail') if isinstance(data, dict) else data
    body = {'detail': str(detail), 'code': _code_for(exc)}
    for key, value in getattr(exc, 'extra', {}).items():
        body.setdefault(key, value)
    response.data = body
    return response
