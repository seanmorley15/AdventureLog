import os
from django.core.management.base import BaseCommand
import requests
from worldtravel.models import Country, Region
from django.db import transaction
import json

from django.conf import settings

COUNTRY_REGION_JSON_VERSION = settings.COUNTRY_REGION_JSON_VERSION
        
media_root = settings.MEDIA_ROOT

def saveCountryFlag(country_code):
    # For standards, use the lowercase country_code
    country_code = country_code.lower()
    flags_dir = os.path.join(media_root, 'flags')

    # Check if the flags directory exists, if not, create it
    if not os.path.exists(flags_dir):
        os.makedirs(flags_dir)

    # Check if the flag already exists in the media folder
    flag_path = os.path.join(flags_dir, f'{country_code}.png')
    if os.path.exists(flag_path):
        print(f'Flag for {country_code} already exists')
        return

    res = requests.get(f'https://flagcdn.com/h240/{country_code}.png'.lower())
    if res.status_code == 200:
        with open(flag_path, 'wb') as f:
            f.write(res.content)
        print(f'Flag for {country_code} downloaded')
    else:
        print(f'Error downloading flag for {country_code}')

class Command(BaseCommand):
    help = 'Imports the world travel data'

    def handle(self, *args, **options):
        countries_json_path = os.path.join(settings.MEDIA_ROOT, f'countries+regions-{COUNTRY_REGION_JSON_VERSION}.json')
        if not os.path.exists(countries_json_path):
            res = requests.get(f'https://raw.githubusercontent.com/dr5hn/countries-states-cities-database/{COUNTRY_REGION_JSON_VERSION}/countries%2Bstates.json')
            if res.status_code == 200:
                with open(countries_json_path, 'w') as f:
                    f.write(res.text)
            else:
                self.stdout.write(self.style.ERROR('Error downloading countries+regions.json'))
                return
            
        with open(countries_json_path, 'r') as f:
            data = json.load(f)

        with transaction.atomic():
            existing_countries = {country.country_code: country for country in Country.objects.all()}
            existing_regions = {region.id: region for region in Region.objects.all()}

            countries_to_create = []
            regions_to_create = []
            countries_to_update = []
            regions_to_update = []

            processed_country_codes = set()
            processed_region_ids = set()

            for country in data:
                country_code = country['iso2']
                country_name = country['name']
                country_subregion = country['subregion']
                country_capital = country['capital']

                processed_country_codes.add(country_code)

                if country_code in existing_countries:
                    country_obj = existing_countries[country_code]
                    country_obj.name = country_name
                    country_obj.subregion = country_subregion
                    country_obj.capital = country_capital
                    countries_to_update.append(country_obj)
                else:
                    country_obj = Country(
                        name=country_name,
                        country_code=country_code,
                        subregion=country_subregion,
                        capital=country_capital
                    )
                    countries_to_create.append(country_obj)

                saveCountryFlag(country_code)
                self.stdout.write(self.style.SUCCESS(f'Country {country_name} prepared'))

                if country['states']:
                    for state in country['states']:
                        name = state['name']
                        state_id = f"{country_code}-{state['state_code']}"
                        latitude = round(float(state['latitude']), 6) if state['latitude'] else None
                        longitude = round(float(state['longitude']), 6) if state['longitude'] else None

                        processed_region_ids.add(state_id)

                        if state_id in existing_regions:
                            region_obj = existing_regions[state_id]
                            region_obj.name = name
                            region_obj.country = country_obj
                            region_obj.longitude = longitude
                            region_obj.latitude = latitude
                            regions_to_update.append(region_obj)
                        else:
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
                    state_id = f"{country_code}-00"
                    processed_region_ids.add(state_id)
                    if state_id in existing_regions:
                        region_obj = existing_regions[state_id]
                        region_obj.name = country_name
                        region_obj.country = country_obj
                        regions_to_update.append(region_obj)
                    else:
                        region_obj = Region(
                            id=state_id,
                            name=country_name,
                            country=country_obj
                        )
                        regions_to_create.append(region_obj)
                    self.stdout.write(self.style.SUCCESS(f'Region {state_id} prepared for {country_name}'))

            # Bulk create new countries and regions
            Country.objects.bulk_create(countries_to_create)
            Region.objects.bulk_create(regions_to_create)

            # Bulk update existing countries and regions
            Country.objects.bulk_update(countries_to_update, ['name', 'subregion', 'capital'])
            Region.objects.bulk_update(regions_to_update, ['name', 'country', 'longitude', 'latitude'])

            # Delete countries and regions that are no longer in the data
            Country.objects.exclude(country_code__in=processed_country_codes).delete()
            Region.objects.exclude(id__in=processed_region_ids).delete()

        self.stdout.write(self.style.SUCCESS('All data imported successfully'))