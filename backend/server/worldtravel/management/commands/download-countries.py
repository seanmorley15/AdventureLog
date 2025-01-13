import os
from django.core.management.base import BaseCommand
import requests
from worldtravel.models import Country, Region, City
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

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force download the countries+regions+states.json file')

    def handle(self, **options):
        force = options['force']
        batch_size = 1000
        countries_json_path = os.path.join(settings.MEDIA_ROOT, f'countries+regions+states-{COUNTRY_REGION_JSON_VERSION}.json')
        if not os.path.exists(countries_json_path) or force:
            res = requests.get(f'https://raw.githubusercontent.com/dr5hn/countries-states-cities-database/{COUNTRY_REGION_JSON_VERSION}/json/countries%2Bstates%2Bcities.json')
            if res.status_code == 200:
                with open(countries_json_path, 'w') as f:
                    f.write(res.text)
                    self.stdout.write(self.style.SUCCESS('countries+regions+states.json downloaded successfully'))
            else:
                self.stdout.write(self.style.ERROR('Error downloading countries+regions+states.json'))
                return
        elif not os.path.isfile(countries_json_path):
            self.stdout.write(self.style.ERROR('countries+regions+states.json is not a file'))
            return
        elif os.path.getsize(countries_json_path) == 0:
            self.stdout.write(self.style.ERROR('countries+regions+states.json is empty'))
        elif Country.objects.count() == 0 or Region.objects.count() == 0 or City.objects.count() == 0:
            self.stdout.write(self.style.WARNING('Some region data is missing. Re-importing all data.'))
        else:
            self.stdout.write(self.style.SUCCESS('Latest country, region, and state data already downloaded.'))
            return
            
        with open(countries_json_path, 'r') as f:
            data = json.load(f)

        with transaction.atomic():
            existing_countries = {country.country_code: country for country in Country.objects.all()}
            existing_regions = {region.id: region for region in Region.objects.all()}
            existing_cities = {city.id: city for city in City.objects.all()}

            countries_to_create = []
            regions_to_create = []
            countries_to_update = []
            regions_to_update = []
            cities_to_create = []
            cities_to_update = []

            processed_country_codes = set()
            processed_region_ids = set()
            processed_city_ids = set()

            for country in data:
                country_code = country['iso2']
                country_name = country['name']
                country_subregion = country['subregion']
                country_capital = country['capital']
                longitude = round(float(country['longitude']), 6) if country['longitude'] else None
                latitude = round(float(country['latitude']), 6) if country['latitude'] else None

                processed_country_codes.add(country_code)

                if country_code in existing_countries:
                    country_obj = existing_countries[country_code]
                    country_obj.name = country_name
                    country_obj.subregion = country_subregion
                    country_obj.capital = country_capital
                    country_obj.longitude = longitude
                    country_obj.latitude = latitude
                    countries_to_update.append(country_obj)
                else:
                    country_obj = Country(
                        name=country_name,
                        country_code=country_code,
                        subregion=country_subregion,
                        capital=country_capital,
                        longitude=longitude,
                        latitude=latitude
                    )
                    countries_to_create.append(country_obj)

                saveCountryFlag(country_code)
                # self.stdout.write(self.style.SUCCESS(f'Country {country_name} prepared'))

                if country['states']:
                    for state in country['states']:
                        name = state['name']
                        state_id = f"{country_code}-{state['state_code']}"
                        latitude = round(float(state['latitude']), 6) if state['latitude'] else None
                        longitude = round(float(state['longitude']), 6) if state['longitude'] else None

                        # Check for duplicate regions
                        if state_id in processed_region_ids:
                            self.stdout.write(self.style.ERROR(f'State {state_id} already processed'))
                            continue

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
                        # self.stdout.write(self.style.SUCCESS(f'State {state_id} prepared'))

                        if 'cities' in state and len(state['cities']) > 0:
                            for city in state['cities']:
                                city_id = f"{state_id}-{city['id']}"
                                city_name = city['name']
                                latitude = round(float(city['latitude']), 6) if city['latitude'] else None
                                longitude = round(float(city['longitude']), 6) if city['longitude'] else None

                                # Check for duplicate cities
                                if city_id in processed_city_ids:
                                    self.stdout.write(self.style.ERROR(f'City {city_id} already processed'))
                                    continue

                                processed_city_ids.add(city_id)

                                if city_id in existing_cities:
                                    city_obj = existing_cities[city_id]
                                    city_obj.name = city_name
                                    city_obj.region = region_obj
                                    city_obj.longitude = longitude
                                    city_obj.latitude = latitude
                                    cities_to_update.append(city_obj)
                                else:
                                    city_obj = City(
                                        id=city_id,
                                        name=city_name,
                                        region=region_obj,
                                        longitude=longitude,
                                        latitude=latitude
                                    )
                                    cities_to_create.append(city_obj)
                                # self.stdout.write(self.style.SUCCESS(f'City {city_id} prepared'))

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
                    # self.stdout.write(self.style.SUCCESS(f'Region {state_id} prepared for {country_name}'))
            # Process in batches
            for i in range(0, len(countries_to_create), batch_size):
                batch = countries_to_create[i:i + batch_size]
                Country.objects.bulk_create(batch)
                self.stdout.write(self.style.SUCCESS(f'Processed countries batch {i//batch_size + 1}/{(len(countries_to_create)-1)//batch_size + 1}'))

            for i in range(0, len(regions_to_create), batch_size):
                batch = regions_to_create[i:i + batch_size]
                Region.objects.bulk_create(batch)
                self.stdout.write(self.style.SUCCESS(f'Processed regions batch {i//batch_size + 1}/{(len(regions_to_create)-1)//batch_size + 1}'))

            for i in range(0, len(cities_to_create), batch_size):
                batch = cities_to_create[i:i + batch_size]
                City.objects.bulk_create(batch)
                self.stdout.write(self.style.SUCCESS(f'Processed cities batch {i//batch_size + 1}/{(len(cities_to_create)-1)//batch_size + 1}'))

            # Process updates in batches
            for i in range(0, len(countries_to_update), batch_size):
                batch = countries_to_update[i:i + batch_size]
                Country.objects.bulk_update(batch, ['name', 'subregion', 'capital'])
                self.stdout.write(self.style.SUCCESS(f'Updated countries batch {i//batch_size + 1}/{(len(countries_to_update)-1)//batch_size + 1}'))

            for i in range(0, len(regions_to_update), batch_size):
                batch = regions_to_update[i:i + batch_size]
                Region.objects.bulk_update(batch, ['name', 'country', 'longitude', 'latitude'])
                self.stdout.write(self.style.SUCCESS(f'Updated regions batch {i//batch_size + 1}/{(len(regions_to_update)-1)//batch_size + 1}'))

            for i in range(0, len(cities_to_update), batch_size):
                batch = cities_to_update[i:i + batch_size]
                City.objects.bulk_update(batch, ['name', 'region', 'longitude', 'latitude'])
                self.stdout.write(self.style.SUCCESS(f'Updated cities batch {i//batch_size + 1}/{(len(cities_to_update)-1)//batch_size + 1}'))
            City.objects.bulk_update(cities_to_update, ['name', 'region', 'longitude', 'latitude'])

            # Delete countries and regions that are no longer in the data
            Country.objects.exclude(country_code__in=processed_country_codes).delete()
            Region.objects.exclude(id__in=processed_region_ids).delete()
            City.objects.exclude(id__in=processed_city_ids).delete()

        self.stdout.write(self.style.SUCCESS('All data imported successfully'))