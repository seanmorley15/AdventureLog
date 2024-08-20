from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


User = get_user_model()

default_user_id = 1  # Replace with an actual user ID

class Country(models.Model):
    AFRICA = 'AF'
    ANTARCTICA = 'AN'
    ASIA = 'AS'
    EUROPE = 'EU'
    NORTH_AMERICA = 'NA'
    OCEANIA = 'OC'
    SOUTH_AMERICA = 'SA'
    
    CONTINENT_CHOICES = [
        (AFRICA, 'Africa'),
        (ANTARCTICA, 'Antarctica'),
        (ASIA, 'Asia'),
        (EUROPE, 'Europe'),
        (NORTH_AMERICA, 'North America'),
        (OCEANIA, 'Oceania'),
        (SOUTH_AMERICA, 'South America'),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    country_code = models.CharField(max_length=2)
    continent = models.CharField(
        max_length=2,
        choices=CONTINENT_CHOICES,
        default=AFRICA
    )

    class Meta:
        verbose_name = "Country"
        verbose_name_plural = "Countries"

    def __str__(self):
        return self.name

class Region(models.Model):
    id = models.CharField(primary_key=True)
    name = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100, blank=True, null=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class VisitedRegion(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
    region = models.ForeignKey(Region, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.region.name} ({self.region.country.country_code}) visited by: {self.user_id.username}'
    
    def save(self, *args, **kwargs):
        if VisitedRegion.objects.filter(user_id=self.user_id, region=self.region).exists():
            raise ValidationError("Region already visited by user.")
        super().save(*args, **kwargs)
