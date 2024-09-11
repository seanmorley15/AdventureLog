import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import requests
from worldtravel.models import Country, Region
from django.db import transaction
from django.contrib.gis.geos import GEOSGeometry, Polygon, MultiPolygon
from django.contrib.gis.geos.error import GEOSException
import json

from django.conf import settings
        
media_root = settings.MEDIA_ROOT


def saveCountryFlag(country_code):
    flags_dir = os.path.join(media_root, 'flags')

    # Check if the flags directory exists, if not, create it
    if not os.path.exists(flags_dir):
        os.makedirs(flags_dir)

    # Check if the flag already exists in the media folder
    flag_path = os.path.join(flags_dir, f'{country_code}.png')
    if os.path.exists(flag_path):
        print(f'Flag for {country_code} already exists')
        return

    res = requests.get(f'https://flagcdn.com/h240/{country_code.lower()}.png'.lower())
    if res.status_code == 200:
        with open(flag_path, 'wb') as f:
            f.write(res.content)
        print(f'Flag for {country_code} downloaded')
    else:
        print(f'Error downloading flag for {country_code}')

class Command(BaseCommand):
    help = 'Imports the world travel data'

    def handle(self, *args, **options):
        countries_json_path = os.path.join(settings.MEDIA_ROOT, 'countries+regions.json')
        if not os.path.exists(countries_json_path):
            res = requests.get('https://raw.githubusercontent.com/dr5hn/countries-states-cities-database/master/countries%2Bstates.json')
            if res.status_code == 200:
                with open(countries_json_path, 'w') as f:
                    f.write(res.text)
            else:
                self.stdout.write(self.style.ERROR('Error downloading countries+regions.json'))
                return
            
        with open(countries_json_path, 'r') as f:
            data = json.load(f)

        countries_to_create = []
        regions_to_create = []

        for country in data:
            country_code = country['iso2']
            country_name = country['name']
            country_subregion = country['subregion']

            country_obj = Country(
                name=country_name,
                country_code=country_code,
                subregion=country_subregion
            )
            countries_to_create.append(country_obj)

            saveCountryFlag(country_code)
            self.stdout.write(self.style.SUCCESS(f'Country {country_name} prepared'))

        # Bulk create countries first
        with transaction.atomic():
            Country.objects.bulk_create(countries_to_create, ignore_conflicts=True)

        # Fetch all countries to get their database IDs
        countries = {country.country_code: country for country in Country.objects.all()}

        for country in data:
            country_code = country['iso2']
            country_obj = countries[country_code]
            
            if country['states']:
                for state in country['states']:
                    name = state['name']
                    state_id = f"{country_code}-{state['state_code']}"
                    latitude = round(float(state['latitude']), 6) if state['latitude'] else None
                    longitude = round(float(state['longitude']), 6) if state['longitude'] else None

                    region_obj = Region(
                        id=state_id,
                        name=name,
                        country=country_obj,
                        longitude=longitude,
                        latitude=latitude
                    )
                    regions_to_create.append(region_obj)
                    self.stdout.write(self.style.SUCCESS(f'State {state_id} prepared'))
            else:
                # Create one region with the name of the country if there are no states
                region_obj = Region(
                    id=f"{country_code}-00",
                    name=country['name'],
                    country=country_obj
                )
                regions_to_create.append(region_obj)
                self.stdout.write(self.style.SUCCESS(f'Region {country_code}-00 prepared for {country["name"]}'))

        # Bulk create regions
        with transaction.atomic():
            Region.objects.bulk_create(regions_to_create, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS('All data imported successfully'))

               
