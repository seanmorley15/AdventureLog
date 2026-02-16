"""
Filtering utilities for viewsets.

This module provides reusable filtering methods that can be mixed into
any viewset that needs visit, public, ownership, or rating filtering.
"""

from django.utils import timezone


class FilteringMixin:
    """
    Mixin providing common filtering methods for viewsets.

    Use this mixin in any viewset that needs to filter querysets by:
    - Visit status (visited/not visited)
    - Public/private status
    - Ownership (mine/public/all)
    - Minimum rating

    Example usage:
        class MyViewSet(FilteringMixin, viewsets.ModelViewSet):
            def list(self, request):
                queryset = self.get_queryset()
                queryset = self.apply_all_filters(queryset, request)
                return Response(...)
    """

    def apply_all_filters(self, queryset, request):
        """
        Apply all standard filters to a queryset.

        Args:
            queryset: The queryset to filter
            request: The HTTP request containing query params

        Returns:
            Filtered queryset
        """
        queryset = self._apply_visit_filtering(queryset, request)
        queryset = self._apply_public_filtering(queryset, request)
        queryset = self._apply_ownership_filtering(queryset, request)
        queryset = self._apply_rating_filtering(queryset, request)
        return queryset

    def _apply_visit_filtering(self, queryset, request):
        """
        Apply visit status filtering to queryset.

        Query params:
            is_visited: 'true', 'false', or 'all' (default: no filter)

        Returns:
            Filtered queryset with only visited or unvisited items
        """
        is_visited_param = request.query_params.get('is_visited')
        if is_visited_param is None or is_visited_param == 'all':
            return queryset

        # Convert parameter to boolean
        if is_visited_param.lower() == 'true':
            is_visited_bool = True
        elif is_visited_param.lower() == 'false':
            is_visited_bool = False
        else:
            return queryset

        # Apply visit filtering based on start_date
        now = timezone.now().date()
        if is_visited_bool:
            queryset = queryset.filter(visits__start_date__lte=now).distinct()
        else:
            queryset = queryset.exclude(visits__start_date__lte=now).distinct()

        return queryset

    def _apply_public_filtering(self, queryset, request):
        """
        Apply public/private filtering to queryset.

        Query params:
            is_public: 'true', 'false', or 'all' (default: no filter)

        Returns:
            Filtered queryset with only public or private items
        """
        is_public_param = request.query_params.get('is_public')
        if is_public_param is None or is_public_param == 'all':
            return queryset

        if is_public_param.lower() == 'true':
            queryset = queryset.filter(is_public=True)
        elif is_public_param.lower() == 'false':
            queryset = queryset.filter(is_public=False)

        return queryset

    def _apply_ownership_filtering(self, queryset, request):
        """
        Apply ownership filtering to queryset.

        Query params:
            ownership: 'mine', 'public', or 'all' (default: no filter)

        Returns:
            Filtered queryset based on ownership
        """
        ownership_param = request.query_params.get('ownership')
        if ownership_param is None or ownership_param == 'all':
            return queryset

        if ownership_param.lower() == 'mine':
            queryset = queryset.filter(user=request.user)
        elif ownership_param.lower() == 'public':
            queryset = queryset.filter(is_public=True).exclude(user=request.user)

        return queryset

    def _apply_rating_filtering(self, queryset, request):
        """
        Apply minimum rating filtering to queryset.

        Query params:
            min_rating: numeric value (1-5) or 'all' (default: no filter)

        Returns:
            Filtered queryset with items having rating >= min_rating
        """
        min_rating_param = request.query_params.get('min_rating')
        if min_rating_param is None or min_rating_param == 'all':
            return queryset

        try:
            min_rating = float(min_rating_param)
            if min_rating > 0:
                queryset = queryset.filter(average_rating__gte=min_rating)
        except (ValueError, TypeError):
            pass

        return queryset
