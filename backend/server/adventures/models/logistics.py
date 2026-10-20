import uuid

from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from djmoney.models.fields import MoneyField

from core.timezones import TIMEZONES

from .base import User, default_user
from .choices import LODGING_TYPES, TRANSPORTATION_TYPES


class Transportation(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=default_user)
    type = models.CharField(max_length=100, choices=TRANSPORTATION_TYPES)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)
    price = MoneyField(max_digits=12, decimal_places=2, default_currency='USD', null=True, blank=True)
    link = models.URLField(blank=True, null=True, max_length=2083)
    date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    start_timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in TIMEZONES], null=True, blank=True)
    end_timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in TIMEZONES], null=True, blank=True)
    flight_number = models.CharField(max_length=100, blank=True, null=True)
    from_location = models.CharField(max_length=200, blank=True, null=True)
    origin = gis_models.PointField(srid=4326, null=True, blank=True)
    destination = gis_models.PointField(srid=4326, null=True, blank=True)
    start_code = models.CharField(max_length=100, blank=True, null=True) # Could be airport code, station code, etc.
    end_code = models.CharField(max_length=100, blank=True, null=True)   # Could be airport code, station code, etc.
    to_location = models.CharField(max_length=200, blank=True, null=True)
    is_public = models.BooleanField(default=False)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Generic relations for images and attachments
    images = GenericRelation('ContentImage', related_query_name='transportation')
    attachments = GenericRelation('ContentAttachment', related_query_name='transportation')

    def clean(self):
        if self.date and self.end_date and self.date > self.end_date:
            raise ValidationError('The start date must be before the end date. Start date: ' + str(self.date) + ' End date: ' + str(self.end_date))
        
        if self.collection:
            if self.user != self.collection.user:
                raise ValidationError('Transportations must be associated with collections owned by the same user. Collection owner: ' + self.collection.user.username + ' Transportation owner: ' + self.user.username)

    def __str__(self):
        return self.name

class Note(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=default_user)
    name = models.CharField(max_length=200)
    content = models.TextField(blank=True, null=True)
    links = ArrayField(models.URLField(), blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    is_public = models.BooleanField(default=False)
    # Hidden from the published story even when the note text group is on.
    is_private = models.BooleanField(default=False)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Generic relations for images and attachments
    images = GenericRelation('ContentImage', related_query_name='note')
    attachments = GenericRelation('ContentAttachment', related_query_name='note')

    def clean(self):
        if self.collection:
            if self.user != self.collection.user:
                raise ValidationError('Notes must be associated with collections owned by the same user. Collection owner: ' + self.collection.user.username + ' Note owner: ' + self.user.username)

    def __str__(self):
        return self.name

class Checklist(models.Model):
    # id = models.AutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user)
    name = models.CharField(max_length=200)
    date = models.DateField(blank=True, null=True)
    is_public = models.BooleanField(default=False)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.collection:
            if self.user != self.collection.user:
                raise ValidationError('Checklists must be associated with collections owned by the same user. Collection owner: ' + self.collection.user.username + ' Checklist owner: ' + self.user.username)

    def __str__(self):
        return self.name

class ChecklistItem(models.Model):
    #id = models.AutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user)
    name = models.CharField(max_length=200)
    is_checked = models.BooleanField(default=False)
    # Hidden from the published story even when the checklist text group is on.
    is_private = models.BooleanField(default=False)
    checklist = models.ForeignKey('Checklist', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.user != self.checklist.user:
            raise ValidationError('Checklist items must be associated with checklists owned by the same user. Checklist owner: ' + self.checklist.user.username + ' Checklist item owner: ' + self.user.username)

    def __str__(self):
        return self.name

class Lodging(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=default_user)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=100, choices=LODGING_TYPES, default='other')
    description = models.TextField(blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)
    link = models.URLField(blank=True, null=True, max_length=2083)
    check_in = models.DateTimeField(blank=True, null=True)
    check_out = models.DateTimeField(blank=True, null=True)
    timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in TIMEZONES], null=True, blank=True)
    reservation_number = models.CharField(max_length=100, blank=True, null=True)
    price = MoneyField(max_digits=12, decimal_places=2, default_currency='USD', null=True, blank=True)
    coordinates = gis_models.PointField(srid=4326, null=True, blank=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    is_public = models.BooleanField(default=False)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Generic relations for images and attachments
    images = GenericRelation('ContentImage', related_query_name='lodging')
    attachments = GenericRelation('ContentAttachment', related_query_name='lodging')

    def clean(self):
        if self.check_in and self.check_out and self.check_in > self.check_out:
            raise ValidationError('The start date must be before the end date. Start date: ' + str(self.check_in) + ' End date: ' + str(self.check_out))
        
        if self.collection:
            if self.user != self.collection.user:
                raise ValidationError('Lodging must be associated with collections owned by the same user. Collection owner: ' + self.collection.user.username + ' Lodging owner: ' + self.user.username)

    def __str__(self):
        return self.name
