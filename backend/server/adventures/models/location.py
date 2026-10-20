import threading
import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import connection, models, transaction
from djmoney.models.fields import MoneyField

from .managers import LocationManager
from adventures.utils.get_is_visited import is_location_visited
from core.geo import has_coordinates
from core.timezones import TIMEZONES
from worldtravel.models import City, Country, Region

from .base import User, default_user


def _coordinate_key(point):
    """A comparable value for a location's point, or None when it has no usable coordinates."""
    if not has_coordinates(point):
        return None
    return (round(point.x, 6), round(point.y, 6))

class Visit(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    location = models.ForeignKey('Location', on_delete=models.CASCADE, related_name='visits')
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in TIMEZONES], null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Generic relations for images and attachments
    images = GenericRelation('ContentImage', related_query_name='visit')
    attachments = GenericRelation('ContentAttachment', related_query_name='visit')

    def clean(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError('The start date must be before or equal to the end date.')

    def __str__(self):
        return f"{self.location.name} - {self.start_date} to {self.end_date}"

class Location(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=default_user)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, blank=True, null=True)
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True, null=True)
    tags = ArrayField(models.CharField(max_length=100), blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)
    price = MoneyField(max_digits=12, decimal_places=2, default_currency='USD', null=True, blank=True)
    link = models.URLField(blank=True, null=True, max_length=2083)
    is_public = models.BooleanField(default=False)
    coordinates = gis_models.PointField(srid=4326, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, blank=True, null=True)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, blank=True, null=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, blank=True, null=True)
    collections = models.ManyToManyField('Collection', blank=True, related_name='locations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Generic relations for images and attachments
    images = GenericRelation('ContentImage', related_query_name='location')
    attachments = GenericRelation('ContentAttachment', related_query_name='location')

    objects = LocationManager()

    def is_visited_status(self):
        return is_location_visited(self)

    def clean(self, skip_shared_validation=False):
        """
        Validate model constraints.
        skip_shared_validation: Skip validation when called by shared users
        """
        # Skip validation if this is a shared user update
        if skip_shared_validation:
            return
            
        # Check collections after the instance is saved (in save method or separate validation)
        if self.pk:  # Only check if the instance has been saved
            for collection in self.collections.all():
                # Only enforce same-user constraint for non-shared collections
                if self.user != collection.user:
                    # Check if this is a shared collection scenario
                    # Allow if the location owner has access to the collection through sharing
                    if not collection.shared_with.filter(uuid=self.user.uuid).exists():
                        raise ValidationError(f'Locations must be associated with collections owned by the same user or shared collections. Collection owner: {collection.user.username} Location owner: {self.user.username}')
        
        if self.category:
            if self.user != self.category.user:
                raise ValidationError(f'Locations must be associated with categories owned by the same user. Category owner: {self.category.user.username} Location owner: {self.user.username}')
            
    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        # Remember the coordinates a stored place was geocoded for, so saving it again
        # without moving it does not geocode it again. A place with no country yet has
        # not been resolved, so it is left to be tried on its next save.
        if 'coordinates' in field_names and ('country_id' not in field_names or instance.country_id):
            instance._geocoded_key = _coordinate_key(instance.coordinates)
        return instance

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None, _skip_geocode=False, _skip_shared_validation=False):
        if force_insert and force_update:
            raise ValueError("Cannot force both insert and updating in model saving.")

        if not self.category:
            category, _ = Category.objects.get_or_create(
                user=self.user,
                name='general',
                defaults={'display_name': 'General', 'icon': '🌍'}
            )
            self.category = category

        result = super().save(
            force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields
        )

        # Validate collections after saving (since M2M relationships require saved instance)
        if self.pk:
            try:
                self.clean(skip_shared_validation=_skip_shared_validation)
            except ValidationError as e:
                # If validation fails, you might want to handle this differently
                # For now, we'll re-raise the error
                raise e

        # Skip threading when called from the geocode worker, and during tests.
        if _skip_geocode or getattr(settings, 'DISABLE_BACKGROUND_GEOCODE', False):
            return result

        # A save that leaves the coordinates alone has nothing new to geocode.
        if update_fields is not None and 'coordinates' not in update_fields:
            return result

        key = _coordinate_key(self.coordinates)
        if key is not None and key != getattr(self, '_geocoded_key', None):
            self._geocoded_key = key
            location_id = str(self.id)

            def run_geocode():
                try:
                    from adventures.services.geocoding.assignment import geocode_and_assign_location
                    geocode_and_assign_location(location_id)
                finally:
                    # The thread opened its own database connection; close it so it does not leak.
                    connection.close()

            def start_geocode():
                thread = threading.Thread(target=run_geocode)
                thread.daemon = True  # Allows the thread to exit when the main program ends
                thread.start()

            # Wait for the row to be committed: the thread reads it back by id.
            transaction.on_commit(start_geocode)

        return result

    def __str__(self):
        return self.name

class Category(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user)
    name = models.CharField(max_length=200)
    display_name = models.CharField(max_length=200)
    icon = models.CharField(max_length=200, default='🌍')

    class Meta:
        verbose_name_plural = 'Categories'
        unique_together = ['name', 'user']

    def clean(self) -> None:
        self.name = self.name.lower().strip()

        return super().clean()
    
    
    def __str__(self):
        return self.name + ' - ' + self.display_name + ' - ' + self.icon
