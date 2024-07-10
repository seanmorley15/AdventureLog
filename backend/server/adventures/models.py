from django.db import models

from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.forms import ValidationError

ADVENTURE_TYPES = [
    ('visited', 'Visited'),
    ('planned', 'Planned'),
    ('featured', 'Featured')
]


# Assuming you have a default user ID you want to use
default_user_id = 1  # Replace with an actual user ID

User = get_user_model()


class Adventure(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
    type = models.CharField(max_length=100, choices=ADVENTURE_TYPES)
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True, null=True)
    activity_types = ArrayField(models.CharField(
        max_length=100), blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    image = models.ImageField(null=True, blank=True, upload_to='images/')
    date = models.DateField(blank=True, null=True)
    is_public = models.BooleanField(default=False)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    trip = models.ForeignKey('Trip', on_delete=models.CASCADE, blank=True, null=True)

    def clean(self):
        if self.trip:
            if self.trip.is_public and not self.is_public:
                raise ValidationError('Adventures associated with a public trip must be public. Trip: ' + self.trip.name + ' Adventure: ' + self.name)
            if self.user_id != self.trip.user_id:
                raise ValidationError('Adventures must be associated with trips owned by the same user. Trip owner: ' + self.trip.user_id.username + ' Adventure owner: ' + self.user_id.username)
            if self.type != self.trip.type:
                raise ValidationError('Adventure type must match trip type. Trip type: ' + self.trip.type + ' Adventure type: ' + self.type)
        if self.type == 'featured' and not self.is_public:
            raise ValidationError('Featured adventures must be public. Adventure: ' + self.name)

    def __str__(self):
        return self.name

class Trip(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=100, choices=ADVENTURE_TYPES)
    location = models.CharField(max_length=200, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    is_public = models.BooleanField(default=False)

    # if connected adventures are private and trip is public, raise an error
    def clean(self):
        if self.is_public and self.pk:  # Only check if the instance has a primary key
            for adventure in self.adventure_set.all():
                if not adventure.is_public:
                    raise ValidationError('Public trips cannot be associated with private adventures. Trip: ' + self.name + ' Adventure: ' + adventure.name)
        if self.type == 'featured' and not self.is_public:
            raise ValidationError('Featured trips must be public. Trip: ' + self.name)

    def __str__(self):
        return self.name