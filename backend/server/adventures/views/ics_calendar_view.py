from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from icalendar import Calendar, Event, vText, vCalAddress
from datetime import datetime, timedelta
from adventures.models import Location
from adventures.serializers import LocationSerializer

class IcsCalendarGeneratorViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def generate(self, request):
        adventures = Location.objects.filter(user=request.user)
        serializer = LocationSerializer(adventures, many=True)
        user = request.user
        name = f"{user.first_name} {user.last_name}"
        
        cal = Calendar()
        cal.add('prodid', '-//My Adventure Calendar//example.com//')
        cal.add('version', '2.0')

        for adventure in serializer.data:
            if adventure['visits']:
                for visit in adventure['visits']:
                    # Skip if start_date is missing
                    if not visit.get('start_date'):
                        continue

                    # Parse start_date and handle end_date
                    try:
                        start_date = datetime.strptime(visit['start_date'], '%Y-%m-%d').date()
                    except ValueError:
                        continue  # Skip if the start_date is invalid

                    end_date = (
                        datetime.strptime(visit['end_date'], '%Y-%m-%d').date() + timedelta(days=1)
                        if visit.get('end_date') else start_date + timedelta(days=1)
                    )
                    
                    # Create event
                    event = Event()
                    event.add('summary', adventure['name'])
                    event.add('dtstart', start_date)
                    event.add('dtend', end_date)
                    event.add('dtstamp', datetime.now())
                    event.add('transp', 'TRANSPARENT')
                    event.add('class', 'PUBLIC')
                    event.add('created', datetime.now())
                    event.add('last-modified', datetime.now())
                    event.add('description', adventure['description'])
                    if adventure.get('location'):
                        event.add('location', adventure['location'])
                    if adventure.get('link'):
                        event.add('url', adventure['link'])
                    
                    organizer = vCalAddress(f'MAILTO:{user.email}')
                    organizer.params['cn'] = vText(name)
                    event.add('organizer', organizer)
                
                    cal.add_component(event)
        
        response = HttpResponse(cal.to_ical(), content_type='text/calendar')
        response['Content-Disposition'] = 'attachment; filename=adventures.ics'
        return response