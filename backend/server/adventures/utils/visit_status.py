"""
Visit status utilities for serializers.

This module provides reusable functions to determine if an object
has been visited, with support for collaborative mode.
"""

from django.utils import timezone
from django.conf import settings


def get_is_visited(obj, request=None):
    """
    Check if an object (Location, Transportation, Lodging) has been visited.

    In collaborative mode, only counts the current user's visits.
    In normal mode, checks all visits.

    Args:
        obj: The object with a 'visits' relationship (Location, Transportation, Lodging)
        request: The HTTP request (optional, required for collaborative mode user check)

    Returns:
        bool: True if the object has been visited, False otherwise
    """
    current_date = timezone.now().date()

    # In collaborative mode, only count the current user's visits
    if getattr(settings, 'COLLABORATIVE_MODE', False):
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user_visits = obj.visits.filter(user=request.user)
            return _has_past_visit(user_visits, current_date)
        # No authenticated user in collab mode = not visited
        return False

    # Normal mode: check all visits
    return _has_past_visit(obj.visits.all(), current_date)


def _has_past_visit(visits, current_date):
    """
    Check if any visit in the queryset has a start_date in the past.

    Args:
        visits: QuerySet of Visit objects
        current_date: The current date to compare against

    Returns:
        bool: True if any visit has a past start_date
    """
    for visit in visits:
        start_date = visit.start_date
        if start_date:
            # Handle datetime vs date
            if isinstance(start_date, timezone.datetime):
                start_date = start_date.date()
            if start_date <= current_date:
                return True
    return False


class VisitStatusMixin:
    """
    Mixin for serializers that need to compute is_visited status.

    Usage:
        class MySerializer(VisitStatusMixin, serializers.ModelSerializer):
            is_visited = serializers.SerializerMethodField()

            # get_is_visited is inherited from the mixin
    """

    def get_is_visited(self, obj):
        """
        SerializerMethodField handler for is_visited.

        Uses the shared get_is_visited utility function.
        """
        request = self.context.get('request')
        return get_is_visited(obj, request)
