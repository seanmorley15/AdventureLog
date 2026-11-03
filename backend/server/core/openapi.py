"""
How the API describes itself (drf-spectacular).

``AutoSchema`` is DRF's ``DEFAULT_SCHEMA_CLASS``. On top of drf-spectacular it

- takes the tag from the viewset's ``openapi_tags`` (falling back to the first path segment),
- writes the summary from the first line of the method's docstring, or a standard phrase
  ("List locations", "Delete a note") for the router's CRUD actions,
- adds the error responses every endpoint can return, all with the ``Error`` body.

``merge_fragments`` is a postprocessing hook that adds hand-written OpenAPI path files
(``settings.OPENAPI_FRAGMENTS``) for routes that are not DRF views.
"""

from pathlib import Path

import yaml
from django.conf import settings
from drf_spectacular.openapi import AutoSchema as SpectacularAutoSchema
from drf_spectacular.utils import OpenApiResponse
from rest_framework import permissions, serializers


class ErrorSerializer(serializers.Serializer):
    detail = serializers.CharField(help_text='A message that can be shown to the user.')
    code = serializers.CharField(
        help_text='A stable machine-readable code, e.g. `not_found`, `permission_denied`, `conflict`.'
    )


class ValidationErrorSerializer(ErrorSerializer):
    fields = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        help_text='Messages for each input that failed validation. '
        '`non_field_errors` holds messages about the request as a whole.',
    )


ERROR_DESCRIPTIONS = {
    '400': 'The request was not valid. `fields` lists the problems for each input.',
    '401': 'No valid credentials were sent (`not_authenticated`), or an API key was rejected '
    '(`authentication_failed`).',
    '403': 'You can see this resource but may not do this to it (`permission_denied`).',
    '404': "The resource does not exist, or you cannot see it (`not_found`).",
    '429': 'Too many requests (`throttled`). Wait and retry.',
}

CRUD_SUMMARIES = {
    'list': 'List {plural}',
    'create': 'Create {article} {singular}',
    'retrieve': 'Get {article} {singular}',
    'update': 'Replace {article} {singular}',
    'partial_update': 'Update {article} {singular}',
    'destroy': 'Delete {article} {singular}',
}

WRITE_METHODS = {'POST', 'PUT', 'PATCH'}


def _first_line(doc):
    return doc.strip().split('\n\n', 1)[0].replace('\n', ' ').strip() if doc else ''


def _rest(doc):
    parts = doc.strip().split('\n\n', 1) if doc else []
    return parts[1].strip() if len(parts) > 1 else ''


class AutoSchema(SpectacularAutoSchema):
    def get_operation_id(self):
        # Name custom actions after the viewset and the action (``immich_album``), so two
        # actions under one path prefix cannot collide. One action serving several methods
        # gets the method too (``collections_member_patch``).
        action = getattr(self.view, 'action', None)
        basename = getattr(self.view, 'basename', None)
        if action and basename and action not in CRUD_SUMMARIES:
            operation_id = f'{basename}_{action}'
            # DRF maps HEAD onto GET itself (in place, so not always yet); count only real methods.
            action_map = getattr(self.view, 'action_map', None) or {}
            methods = [m for m, a in action_map.items() if a == action and m not in ('head', 'options')]
            if len(methods) > 1:
                operation_id += f'_{self.method.lower()}'
            return operation_id.replace('-', '_')
        return super().get_operation_id()

    def get_tags(self):
        tags = getattr(self.view, 'openapi_tags', None)
        if tags:
            return list(tags)
        return super().get_tags()

    def _action_doc(self):
        action = getattr(self.view, 'action', None) or self.method.lower()
        handler = getattr(self.view, action, None)
        return (getattr(handler, '__doc__', None) or '').strip(), action

    def _resource_names(self):
        singular = getattr(self.view, 'openapi_resource', None)
        if not singular:
            queryset = getattr(self.view, 'queryset', None)
            model = getattr(queryset, 'model', None) or getattr(self.view, 'model', None)
            if model is None:
                serializer_class = getattr(self.view, 'serializer_class', None)
                model = getattr(getattr(serializer_class, 'Meta', None), 'model', None)
            if model is None:
                return None, None
            singular = str(model._meta.verbose_name)
        plural = getattr(self.view, 'openapi_resource_plural', None) or f'{singular}s'
        return singular, plural

    def get_summary(self):
        doc, action = self._action_doc()
        if doc and action not in CRUD_SUMMARIES:
            return _first_line(doc)
        if action in CRUD_SUMMARIES:
            if doc:
                return _first_line(doc)
            singular, plural = self._resource_names()
            if singular:
                article = 'an' if singular[0].lower() in 'aeiou' else 'a'
                return CRUD_SUMMARIES[action].format(article=article, singular=singular, plural=plural)
        return None

    def get_description(self):
        doc, action = self._action_doc()
        if doc:
            return _rest(doc)
        if action in CRUD_SUMMARIES:
            # The resource description, shown once per standard action.
            return super().get_description()
        return ''

    def _allows_anonymous(self):
        perms = [p.__class__ for p in self.view.get_permissions()]
        return permissions.AllowAny in perms or not perms

    def _get_response_bodies(self, direction='response'):
        responses = super()._get_response_bodies(direction)
        if direction != 'response':
            return responses

        def add(code, serializer):
            if code not in responses:
                responses[code] = self._get_response_for_code(
                    OpenApiResponse(serializer, description=ERROR_DESCRIPTIONS[code]), code, direction=direction
                )

        has_path_params = '{' in self.path
        if self.method in WRITE_METHODS or (self.method == 'GET' and self._has_query_parameters()):
            add('400', ValidationErrorSerializer)
        if not self._allows_anonymous():
            add('401', ErrorSerializer)
        if self.method in WRITE_METHODS or self.method == 'DELETE' or has_path_params:
            add('403', ErrorSerializer)
        if has_path_params:
            add('404', ErrorSerializer)
        if getattr(self.view, 'throttle_classes', None):
            add('429', ErrorSerializer)
        return dict(sorted(responses.items()))

    def _has_query_parameters(self):
        return any(
            param.get('in') == 'query' for param in self._get_parameters()
            if param.get('name') not in ('format',)
        )

    def _get_paginator(self):
        # Only the list action and actions that set a paginator on themselves are paged.
        paginator = super()._get_paginator()
        if paginator is None:
            return None
        if getattr(self.view, 'action', None) == 'list' or getattr(self.view, 'paginate_action', False):
            return paginator
        return None


def file_response(media_type, description):
    """A binary download, for ``extend_schema(responses=...)``."""
    return OpenApiResponse(
        response={'type': 'string', 'format': 'binary'},
        description=description,
    ), media_type


def merge_fragments(result, generator, request, public):
    """Add the paths and components in ``settings.OPENAPI_FRAGMENTS`` to the schema."""
    for fragment_path in getattr(settings, 'OPENAPI_FRAGMENTS', []):
        fragment = yaml.safe_load(Path(fragment_path).read_text())
        for operations in fragment.get('paths', {}).values():
            for operation in operations.values():
                # These routes use the session cookie; an operation lists `security: [{}]` when it is public.
                operation.setdefault('security', [{'cookieAuth': []}])
        result.setdefault('paths', {}).update(fragment.get('paths', {}))
        for section, entries in (fragment.get('components') or {}).items():
            result.setdefault('components', {}).setdefault(section, {}).update(entries)
    return result


__all__ = [
    'AutoSchema',
    'ErrorSerializer',
    'ValidationErrorSerializer',
    'file_response',
    'merge_fragments',
]
