from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.gis.db import models as gis_models
from core.geo import first_usable_lat_lon, point_to_lat_lon


User = get_user_model()

default_user = 1  # Replace with an actual user ID


class Country(models.Model):

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    country_code = models.CharField(max_length=2, unique=True) #iso2 code
    subregion = models.CharField(max_length=100, blank=True, null=True)
    capital = models.CharField(max_length=100, blank=True, null=True)
    native_name = models.CharField(max_length=255, blank=True, null=True)  # the name in its own language
    coordinates = gis_models.PointField(srid=4326, null=True, blank=True)

    class Meta:
        verbose_name = "Country"
        verbose_name_plural = "Countries"

    @property
    def latitude(self):
        lat, _ = point_to_lat_lon(self.coordinates)
        return lat

    @property
    def longitude(self):
        _, lon = point_to_lat_lon(self.coordinates)
        return lon

    def __str__(self):
        return self.name

class Region(models.Model):
    id = models.CharField(primary_key=True)
    name = models.CharField(max_length=100)
    native_name = models.CharField(max_length=255, blank=True, null=True)  # the name in its own language
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    # Set when the dataset lists this region of a country as a country of its own too (an
    # overseas region of France that is also a Country). Geocoders report such a place under
    # its parent, and this is how it is tied to the entry it should be filed under.
    territory = models.ForeignKey(
        Country, on_delete=models.SET_NULL, null=True, blank=True, related_name='territory_regions'
    )
    coordinates = gis_models.PointField(srid=4326, null=True, blank=True)

    def resolved_lat_lon(self):
        """Region centroid, or the parent country when the dataset has no region coords.

        City-states (Vatican, Monaco, Singapore, …) are imported as a single
        synthetic region with no coordinates of their own.
        """
        country_coords = self.country.coordinates if self.country_id else None
        return first_usable_lat_lon(self.coordinates, country_coords)

    @property
    def latitude(self):
        lat, _ = self.resolved_lat_lon()
        return lat

    @property
    def longitude(self):
        _, lon = self.resolved_lat_lon()
        return lon

    def __str__(self):
        return self.name
    
class City(models.Model):
    id = models.CharField(primary_key=True)
    name = models.CharField(max_length=100)
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    coordinates = gis_models.PointField(srid=4326, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Cities"

    @property
    def latitude(self):
        lat, _ = point_to_lat_lon(self.coordinates)
        return lat

    @property
    def longitude(self):
        _, lon = point_to_lat_lon(self.coordinates)
        return lon

    def __str__(self):
        return self.name

class CityAlias(models.Model):
    """
    An id a city used to have.

    The world data listed some towns twice (Puerto Rico's under the country and under the US
    region), and the import keeps one. This remembers the id of the one it dropped, so a backup
    made before that still finds its city.
    """

    old_id = models.CharField(primary_key=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='aliases')

    class Meta:
        verbose_name_plural = "City aliases"

    def __str__(self):
        return f'{self.old_id} -> {self.city_id}'


class VisitedRegion(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user)
    region = models.ForeignKey(Region, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.region.name} ({self.region.country.country_code}) visited by: {self.user.username}'
    
    def save(self, *args, **kwargs):
        if VisitedRegion.objects.filter(user=self.user, region=self.region).exclude(pk=self.pk).exists():
            raise ValidationError("Region already visited by user.")
        super().save(*args, **kwargs)

class VisitedCity(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user)
    city = models.ForeignKey(City, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.city.name} ({self.city.region.name}) visited by: {self.user.username}'
    
    def save(self, *args, **kwargs):
        if VisitedCity.objects.filter(user=self.user, city=self.city).exclude(pk=self.pk).exists():
            raise ValidationError("City already visited by user.")
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Visited Cities"
