from django.utils import timezone


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
        start_date = visit.start_date.date() if isinstance(visit.start_date, timezone.datetime) else visit.start_date
        end_date = visit.end_date.date() if isinstance(visit.end_date, timezone.datetime) else visit.end_date
        
        if start_date and end_date and (start_date <= current_date):
            return True
        elif start_date and not end_date and (start_date <= current_date):
            return True
            
    return False