from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from icalendar import Calendar, Event, vText, vCalAddress
from datetime import datetime, timedelta
from django.db.models import Prefetch
from adventures.models import Location, Visit

class IcsCalendarGeneratorViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def generate(self, request):
        locations = (
            Location.objects.filter(user=request.user)
            .prefetch_related(
                Prefetch(
                    'visits',
                    queryset=Visit.objects.only('id', 'start_date', 'end_date')
                )
            )
            .only('id', 'name', 'description', 'location', 'link')
        )

        user = request.user
        name = f"{user.first_name} {user.last_name}"

        cal = Calendar()
        cal.add('prodid', '-//My Adventure Calendar//example.com//')
        cal.add('version', '2.0')

        for location in locations:
            visits = list(location.visits.all())
            if not visits:
                continue

            for visit in visits:
                start_value = getattr(visit, 'start_date', None)
                if not start_value:
                    continue

                # Normalize start date
                if isinstance(start_value, str):
                    try:
                        start_dt = datetime.fromisoformat(start_value.replace('Z', '+00:00'))
                    except ValueError:
                        continue
                else:
                    start_dt = start_value

                start_date = start_dt.date() if hasattr(start_dt, 'date') else start_dt

                # Normalize end date (inclusive of final day)
                end_value = getattr(visit, 'end_date', None) or start_dt
                if isinstance(end_value, str):
                    try:
                        end_dt = datetime.fromisoformat(end_value.replace('Z', '+00:00'))
                    except ValueError:
                        end_dt = start_dt
                else:
                    end_dt = end_value

                end_date = end_dt.date() if hasattr(end_dt, 'date') else end_dt
                end_date = end_date + timedelta(days=1)

                event = Event()
                event.add('summary', location.name)
                event.add('dtstart', start_date)
                event.add('dtend', end_date)
                event.add('dtstamp', datetime.now())
                event.add('transp', 'TRANSPARENT')
                event.add('class', 'PUBLIC')
                event.add('created', datetime.now())
                event.add('last-modified', datetime.now())
                event.add('description', getattr(location, 'description', '') or '')

                if getattr(location, 'location', None):
                    event.add('location', location.location)

                if getattr(location, 'link', None):
                    event.add('url', location.link)

                organizer = vCalAddress(f'MAILTO:{user.email}')
                organizer.params['cn'] = vText(name)
                event.add('organizer', organizer)

                cal.add_component(event)

        response = HttpResponse(cal.to_ical(), content_type='text/calendar')
        response['Content-Disposition'] = 'attachment; filename=locations.ics'
        return response