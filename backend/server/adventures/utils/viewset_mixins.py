"""
Viewset utility mixins for sorting, pagination, and common operations.

This module provides reusable methods that can be mixed into any viewset
that needs sorting, ordering, or pagination functionality.
"""

from django.db.models import Max
from django.db.models.functions import Lower
from rest_framework.response import Response


class SortingMixin:
    """
    Mixin providing sorting and ordering methods for viewsets.

    Subclasses can override `valid_order_fields` to customize allowed fields.

    Example usage:
        class MyViewSet(SortingMixin, viewsets.ModelViewSet):
            valid_order_fields = ['name', 'created_at', 'updated_at']

            def list(self, request):
                queryset = self.get_queryset()
                queryset = self.apply_sorting(queryset)
                return Response(...)
    """

    # Override in subclass to customize allowed sort fields
    valid_order_fields = ['name', 'last_visit', 'rating', 'updated_at', 'created_at']
    default_order_field = 'updated_at'
    default_order_direction = 'asc'

    def apply_sorting(self, queryset):
        """
        Apply sorting to queryset based on query params.

        Query params:
            order_by: field name to sort by
            order_direction: 'asc' or 'desc'

        Returns:
            Sorted queryset
        """
        order_by = self.request.query_params.get('order_by', self.default_order_field)
        order_direction = self.request.query_params.get('order_direction', self.default_order_direction)

        # Validate parameters
        if order_by not in self.valid_order_fields:
            order_by = self.default_order_field

        if order_direction not in ['asc', 'desc']:
            order_direction = self.default_order_direction

        return self._apply_ordering(queryset, order_by, order_direction)

    def _apply_ordering(self, queryset, order_by, order_direction):
        """
        Apply ordering to queryset based on field type.

        Handles special cases:
            - last_visit: Annotates with latest visit date
            - name: Case-insensitive ordering
            - rating: Filters out null ratings
            - updated_at: Reverse default order (newest first)

        Args:
            queryset: The queryset to order
            order_by: Field name to order by
            order_direction: 'asc' or 'desc'

        Returns:
            Ordered queryset
        """
        if order_by == 'last_visit':
            queryset = queryset.annotate(
                latest_visit=Max('visits__start_date')
            ).filter(latest_visit__isnull=False)
            ordering = 'latest_visit'
        elif order_by == 'name':
            queryset = queryset.annotate(lower_name=Lower('name'))
            ordering = 'lower_name'
        elif order_by == 'rating':
            queryset = queryset.filter(average_rating__isnull=False)
            ordering = 'average_rating'
        elif order_by == 'updated_at':
            # Special handling for updated_at (reverse default order)
            ordering = '-updated_at' if order_direction == 'asc' else 'updated_at'
            return queryset.order_by(ordering)
        elif order_by == 'created_at':
            ordering = 'created_at'
        else:
            ordering = order_by

        # Apply direction
        if order_direction == 'desc':
            ordering = f'-{ordering}'

        return queryset.order_by(ordering)


class PaginationMixin:
    """
    Mixin providing pagination helper methods for viewsets.

    Requires the viewset to have a `pagination_class` attribute set.

    Example usage:
        class MyViewSet(PaginationMixin, viewsets.ModelViewSet):
            pagination_class = StandardResultsSetPagination

            def list(self, request):
                queryset = self.get_queryset()
                return self.paginate_and_respond(queryset, request)
    """

    def paginate_and_respond(self, queryset, request):
        """
        Paginate queryset and return appropriate response.

        Args:
            queryset: The queryset to paginate
            request: The HTTP request

        Returns:
            Response with paginated data or full queryset if no pagination
        """
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ViewsetUtilsMixin(SortingMixin, PaginationMixin):
    """
    Combined mixin providing both sorting and pagination utilities.

    This is a convenience mixin that combines SortingMixin and PaginationMixin.

    Example usage:
        class MyViewSet(ViewsetUtilsMixin, viewsets.ModelViewSet):
            pagination_class = StandardResultsSetPagination
            valid_order_fields = ['name', 'created_at']

            def list(self, request):
                queryset = self.get_queryset()
                queryset = self.apply_sorting(queryset)
                return self.paginate_and_respond(queryset, request)
    """
    pass
