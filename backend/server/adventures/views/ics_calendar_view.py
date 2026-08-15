from datetime import datetime, timedelta

from django.http import HttpResponse
from icalendar import Calendar, Event, vCalAddress, vText
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from adventures.services.calendar_events import iter_calendar_events_for_ics


def _parse_event_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None


class IcsCalendarGeneratorViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def generate(self, request):
        user = request.user
        name = f'{user.first_name} {user.last_name}'.strip() or user.username

        cal = Calendar()
        cal.add('prodid', '-//AdventureLog Calendar//adventurelog.app//')
        cal.add('version', '2.0')
        cal.add('calscale', 'GREGORIAN')
        cal.add('method', 'PUBLISH')
        cal.add('x-wr-calname', 'AdventureLog')

        for item in iter_calendar_events_for_ics(user):
            start_dt = _parse_event_datetime(item.get('start'))
            if not start_dt:
                continue

            end_dt = _parse_event_datetime(item.get('end')) or start_dt
            all_day = bool(item.get('all_day'))

            event = Event()
            event.add('uid', f"{item['id']}@adventurelog")
            event.add('summary', f"{item.get('icon', '')} {item.get('title', 'Event')}".strip())
            event.add('dtstamp', datetime.now())
            event.add('transp', 'TRANSPARENT')
            event.add('class', 'PUBLIC')
            event.add('created', datetime.now())
            event.add('last-modified', datetime.now())

            if item.get('description'):
                event.add('description', item['description'])
            if item.get('location_label'):
                event.add('location', item['location_label'])
            if item.get('url'):
                event.add('url', item['url'])

            categories = [item.get('category', 'Adventure')]
            if item.get('collection_name'):
                categories.append(item['collection_name'])
            event.add('categories', categories)

            if all_day:
                start_date = start_dt.date()
                end_date = end_dt.date() + timedelta(days=1)
                event.add('dtstart', start_date)
                event.add('dtend', end_date)
            else:
                event.add('dtstart', start_dt)
                event.add('dtend', end_dt if end_dt >= start_dt else start_dt)

            organizer = vCalAddress(f'MAILTO:{user.email}')
            organizer.params['cn'] = vText(name)
            event.add('organizer', organizer)

            cal.add_component(event)

        response = HttpResponse(cal.to_ical(), content_type='text/calendar')
        response['Content-Disposition'] = 'attachment; filename=adventurelog.ics'
        return response
