"""Shared setup for the day-plan tests."""

from datetime import date, datetime, timezone
from urllib.parse import urlencode

from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APITestCase

from adventures.models import Collection, CollectionItineraryDay, CollectionItineraryItem, Location
from users.models import CustomUser


def utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def ct(model):
    return ContentType.objects.get_for_model(model)


def item_url(collection, item_id=None, action=None):
    """``/api/collections/<id>/itinerary-items/[<item>/[<action>/]]``."""
    url = f'/api/collections/{getattr(collection, "id", collection)}/itinerary-items/'
    if item_id is not None:
        url += f'{item_id}/'
    if action:
        url += f'{action}/'
    return url


def plan_request(client, collection, action, payload=None):
    """
    Send a day plan change. ``action`` names it (``days/insert``, ``days/delete``, ``duration``,
    ``log-day``...); ``payload`` may carry the ``day`` it is about.
    """
    payload = dict(payload or {})
    base = f'/api/collections/{getattr(collection, "id", collection)}'
    day = payload.pop('day', None)
    if action == 'days/insert':
        return client.post(f'{base}/days/', payload, format='json')
    if action == 'days/delete':
        query = f'?{urlencode(payload)}' if payload else ''
        return client.delete(f'{base}/days/{day}/{query}')
    if action in ('days/move', 'days/duplicate'):
        return client.post(f'{base}/days/{day}/{action.split("/")[1]}/', payload, format='json')
    if action == 'log-day':
        return client.post(f'{base}/days/{day}/log-visit/', payload, format='json')
    return client.post(f'{base}/itinerary/{action}/', payload, format='json')


class DayPlanTestBase(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='day-plan-user', email='day-plan@example.com', password='testpassword123'
        )
        self.client.force_authenticate(user=self.user)

    def make_trip(self, start=date(2026, 6, 1), end=date(2026, 6, 5), **kwargs):
        return Collection.objects.create(user=self.user, name='Trip', type='trip', start_date=start, end_date=end, **kwargs)

    def location(self, name='Museum', collection=None):
        location = Location.objects.create(user=self.user, name=name)
        if collection is not None:
            location.collections.add(collection)
        return location

    def row(self, collection, obj, *, on=None, is_global=False, order=0):
        return CollectionItineraryItem.objects.create(
            collection=collection,
            content_type=ct(type(obj)),
            object_id=obj.id,
            date=on,
            is_global=is_global,
            order=order,
        )

    def days(self, collection):
        return list(collection.itinerary_days.filter(index__isnull=False).order_by('index'))

    def placements(self, collection, obj):
        return list(
            CollectionItineraryItem.objects.filter(collection=collection, object_id=obj.id)
            .select_related('day')
            .order_by('day__index')
        )

    def day(self, collection, index):
        return CollectionItineraryDay.objects.get(collection=collection, index=index)
