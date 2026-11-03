from django.http import HttpResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from adventures.serializers.calendar import CalendarEventsSerializer, CalendarQuerySerializer
from adventures.services.calendar_events import build_ics_calendar, get_calendar_events_for_user
from core.serializers import validated


class CalendarViewSet(viewsets.ViewSet):
    """Visits, stays, transport, trips, notes and checklists with a date, as calendar events."""

    openapi_tags = ['Calendar']

    @extend_schema(parameters=[CalendarQuerySerializer], responses=CalendarEventsSerializer)
    @action(detail=False, methods=['get'])
    def events(self, request):
        """
        List calendar events

        Your dated records as events, sorted by start. Limit them to a date range with `start`
        and `end`, and to some kinds with `types`.
        """
        params = validated(CalendarQuerySerializer, request.query_params)
        events = get_calendar_events_for_user(
            request.user,
            start=params['start'].isoformat() if params.get('start') else None,
            end=params['end'].isoformat() if params.get('end') else None,
            types=params.get('types'),
        )
        return Response({'count': len(events), 'events': events})

    @extend_schema(
        responses={(200, 'text/calendar'): OpenApiResponse(response=bytes, description='An iCalendar file.')},
    )
    @action(detail=False, methods=['get'])
    def ics(self, request):
        """
        Download as iCalendar

        Every event as an `.ics` file to import into a calendar app.
        """
        response = HttpResponse(build_ics_calendar(request.user), content_type='text/calendar')
        response['Content-Disposition'] = 'attachment; filename=adventurelog.ics'
        return response
