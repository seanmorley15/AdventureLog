"""What kind of collection or item something is, and which days a collection has."""

from __future__ import annotations


from django.apps import apps as global_apps

from .errors import DayPlanError


class Registry:
    def __init__(self, apps=None):
        get_model = (apps or global_apps).get_model
        self.Collection = get_model('adventures', 'Collection')
        self.Day = get_model('adventures', 'CollectionItineraryDay')
        self.Item = get_model('adventures', 'CollectionItineraryItem')
        self.Visit = get_model('adventures', 'Visit')
        self.Location = get_model('adventures', 'Location')
        self.Lodging = get_model('adventures', 'Lodging')
        self.Transportation = get_model('adventures', 'Transportation')
        self.Note = get_model('adventures', 'Note')
        self.Checklist = get_model('adventures', 'Checklist')
        self.ContentType = get_model('contenttypes', 'ContentType')
        self._ct_cache = {}
        self._ct_names = {}

    def ct(self, name):
        if name not in self._ct_cache:
            ct, _ = self.ContentType.objects.get_or_create(app_label='adventures', model=name)
            self._ct_cache[name] = ct
            self._ct_names[ct.pk] = name
        return self._ct_cache[name]

    def ct_name(self, ct_id):
        if ct_id not in self._ct_names:
            ct = self.ContentType.objects.filter(pk=ct_id).first()
            self._ct_names[ct_id] = ct.model if ct else None
        return self._ct_names[ct_id]

def is_day_based(collection, registry=None) -> bool:
    reg = registry or Registry()
    return reg.Day.objects.filter(collection_id=collection.pk, index__isnull=False).exists()

def has_legacy_dated_items(collection) -> bool:
    """Date-keyed rows that have not been converted to a day index."""
    from adventures.models import CollectionItineraryItem

    return CollectionItineraryItem.objects.filter(
        collection=collection, date__isnull=False, day__isnull=True
    ).exists()

def indexed_days(collection, registry=None):
    reg = registry or Registry()
    return list(reg.Day.objects.filter(collection_id=collection.pk, index__isnull=False).order_by('index'))

def day_count(collection, registry=None):
    # List endpoints annotate this to avoid one count query per collection.
    if hasattr(collection, 'day_count_annotated'):
        return collection.day_count_annotated
    reg = registry or Registry()
    return reg.Day.objects.filter(collection_id=collection.pk, index__isnull=False).count()

def item_kind(item):
    return item.content_type.model

def require_day_based(collection):
    if not is_day_based(collection):
        raise DayPlanError('This trip is not planned by days yet.', code='not_day_based')

def get_day(collection, day_id):
    from adventures.models import CollectionItineraryDay

    if day_id is None:
        raise DayPlanError('A day is required.')
    try:
        return CollectionItineraryDay.objects.get(collection=collection, pk=day_id, index__isnull=False)
    except (CollectionItineraryDay.DoesNotExist, ValueError, TypeError):
        from django.core.exceptions import ValidationError as DjangoValidationError

        raise DayPlanError('Day not found.', code='not_found')
    except DjangoValidationError:
        raise DayPlanError('Day not found.', code='not_found')

def get_day_by_index(collection, index):
    from adventures.models import CollectionItineraryDay

    try:
        return CollectionItineraryDay.objects.get(collection=collection, index=int(index))
    except (CollectionItineraryDay.DoesNotExist, ValueError, TypeError):
        raise DayPlanError('Day not found.', code='not_found')
