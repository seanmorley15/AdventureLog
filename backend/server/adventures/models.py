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
            if self.is_public and not self.trip.is_public:
                raise ValidationError('Public adventures must be associated with a public trip')
            if self.trip.is_public and not self.is_public:
                raise ValidationError('Adventures associated with a public trip must be public')
            if self.user_id != self.trip.user_id:
                raise ValidationError('Adventures must be associated with trips owned by the same user')
        elif self.is_public:
            raise ValidationError('Public adventures must be associated with a trip')

class Trip(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=100, choices=ADVENTURE_TYPES)
    location = models.CharField(max_length=200, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    is_public = models.BooleanField(default=False)

    def clean(self):
            if self.is_public:
                if self.adventures.filter(is_public=False).exists():
                    raise ValidationError('Public trips cannot have private adventures')

    def __str__(self):
        return self.name
