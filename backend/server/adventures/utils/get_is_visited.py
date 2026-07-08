from datetime import datetime, timezone as dt_timezone

from django.utils import timezone


def _visit_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            value = timezone.make_aware(value, dt_timezone.utc)
        return value.date()
    return value


def is_location_visited(location):
    """
    Check if a location has been visited based on its visits.
    
    Args:
        location: Location instance with visits relationship
        
    Returns:
        bool: True if location has been visited, False otherwise
    """
    current_date = timezone.now().date()
    
    for visit in location.visits.all():
        start_date = _visit_date(visit.start_date)
        end_date = _visit_date(visit.end_date)
        
        if start_date and end_date and (start_date <= current_date):
            return True
        elif start_date and not end_date and (start_date <= current_date):
            return True
            
    return False
