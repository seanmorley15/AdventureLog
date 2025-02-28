from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.gis.db import models as gis_models
from cities.models import Country as CityCountry, City as CityCity, Region as CityRegion

User = get_user_model()

default_user_id = 1  # Replace with an actual user ID

class Country(models.Model):

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    country_code = models.CharField(max_length=2, unique=True) #iso2 code
    subregion = models.CharField(max_length=100, blank=True, null=True)
    capital = models.CharField(max_length=100, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    insert_id = models.UUIDField(unique=False, blank=True, null=True)
    translations = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = "Country"
        verbose_name_plural = "Countries"

    def __str__(self):
        return self.name
    
    def get_translations(self, languages: list[str])->bool:
        # get the translations for the country
        translations = self.translations
        try:
            # get the preferred alt names for the country
            alt_names = CityCountry.objects.get(code=self.country_code).alt_names.filter(language_code__in=languages, is_preferred=True)
            for alt_name in alt_names:
                translations[alt_name.language_code] = alt_name.name
            
            if self.translations != translations:
                self.translations = translations
                return True
            return False
        except CityCountry.DoesNotExist:
            print(f"Country {self.name} ({self.country_code}) not found in cities.models.Country")
            return False

class Region(models.Model):
    id = models.CharField(primary_key=True)
    name = models.CharField(max_length=100)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    insert_id = models.UUIDField(unique=False, blank=True, null=True)

    def __str__(self):
        return self.name
    
class City(models.Model):
    id = models.CharField(primary_key=True)
    name = models.CharField(max_length=100)
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    insert_id = models.UUIDField(unique=False, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Cities"

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

class VisitedCity(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
    city = models.ForeignKey(City, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.city.name} ({self.city.region.name}) visited by: {self.user_id.username}'
    
    def save(self, *args, **kwargs):
        if VisitedCity.objects.filter(user_id=self.user_id, city=self.city).exists():
            raise ValidationError("City already visited by user.")
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Visited Cities"