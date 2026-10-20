from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from adventures.services.calendar_events import get_calendar_events_for_user


class CalendarViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def events(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'User is not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

        events = get_calendar_events_for_user(
            request.user,
            start=request.query_params.get('start'),
            end=request.query_params.get('end'),
            types=request.query_params.get('types'),
        )
        return Response({'events': events, 'count': len(events)})
