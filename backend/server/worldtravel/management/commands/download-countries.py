import os
from django.core.management.base import BaseCommand
import requests
from worldtravel.models import Country, Region, City
from django.db import transaction
from tqdm import tqdm
import ijson

from django.conf import settings

ADVENTURELOG_CDN_URL = settings.ADVENTURELOG_CDN_URL
        
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

    res = requests.get(f'{ADVENTURELOG_CDN_URL}/data/flags/{country_code}.png'.lower())
    if res.status_code == 200:
        with open(flag_path, 'wb') as f:
            f.write(res.content)
        print(f'Flag for {country_code} downloaded')
    else:
        print(f'Error downloading flag for {country_code}')

class Command(BaseCommand):
    help = 'Imports the world travel data'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force re-download of AdventureLog setup content from the CDN')

    def handle(self, **options):
        force = options['force']
        batch_size = 100
        current_version_json = os.path.join(settings.MEDIA_ROOT, 'data_version.json')
        cdn_version_json = requests.get(f'{ADVENTURELOG_CDN_URL}/data/version.json')
        if cdn_version_json.status_code == 200:
            cdn_version = cdn_version_json.json().get('version')
            if os.path.exists(current_version_json):
                with open(current_version_json, 'r') as f:
                    local_version = f.read().strip()
                    self.stdout.write(self.style.SUCCESS(f'Local version: {local_version}'))
            else:
                local_version = None

            if force or local_version != cdn_version:
                with open(current_version_json, 'w') as f:
                    f.write(cdn_version)
                    self.stdout.write(self.style.SUCCESS('Version updated successfully to ' + cdn_version))
            else:
                self.stdout.write(self.style.SUCCESS('Data is already up-to-date. Run with --force to re-download'))
                return
        else:
            self.stdout.write(self.style.ERROR('Error downloading version.json'))
            return
        
        self.stdout.write(self.style.SUCCESS('Fetching latest data from the AdventureLog CDN located at: ' + ADVENTURELOG_CDN_URL))

        # Delete the existing flags
        flags_dir = os.path.join(media_root, 'flags')
        if os.path.exists(flags_dir):
            for file in os.listdir(flags_dir):
                os.remove(os.path.join(flags_dir, file))

        # Delete the existing countries, regions, and cities json files
        countries_json_path = os.path.join(media_root, 'countries_states_cities.json')
        if os.path.exists(countries_json_path):
            os.remove(countries_json_path)
            self.stdout.write(self.style.SUCCESS('countries_states_cities.json deleted successfully'))

        # Download the latest countries, regions, and cities json file
        res = requests.get(f'{ADVENTURELOG_CDN_URL}/data/countries_states_cities.json')
        if res.status_code == 200:
            with open(countries_json_path, 'w') as f:
                f.write(res.text)
                self.stdout.write(self.style.SUCCESS('countries_states_cities.json downloaded successfully'))
        else:
            self.stdout.write(self.style.ERROR('Error downloading countries_states_cities.json'))
            return
            

        # if not os.path.exists(version_json) or force:
        #     res = requests.get(f'https://raw.githubusercontent.com/dr5hn/countries-states-cities-database/{COUNTRY_REGION_JSON_VERSION}/json/countries%2Bstates%2Bcities.json')
        #     if res.status_code == 200:
        #         with open(countries_json_path, 'w') as f:
        #             f.write(res.text)
        #             self.stdout.write(self.style.SUCCESS('countries+regions+states.json downloaded successfully'))
        #     else:
        #         self.stdout.write(self.style.ERROR('Error downloading countries+regions+states.json'))
        #         return
        # elif not os.path.isfile(countries_json_path):
        #     self.stdout.write(self.style.ERROR('countries+regions+states.json is not a file'))
        #     return
        # elif os.path.getsize(countries_json_path) == 0:
        #     self.stdout.write(self.style.ERROR('countries+regions+states.json is empty'))
        # elif Country.objects.count() == 0 or Region.objects.count() == 0 or City.objects.count() == 0:
        #     self.stdout.write(self.style.WARNING('Some region data is missing. Re-importing all data.'))
        # else:
        #     self.stdout.write(self.style.SUCCESS('Latest country, region, and state data already downloaded.'))
        #     return
            
        with open(countries_json_path, 'r') as f:
            f = open(countries_json_path, 'rb')
            parser = ijson.items(f, 'item')

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

            for country in parser:
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

                if country['states']:
                    for state in country['states']:
                        name = state['name']
                        state_id = f"{country_code}-{state['state_code']}"
                        latitude = round(float(state['latitude']), 6) if state['latitude'] else None
                        longitude = round(float(state['longitude']), 6) if state['longitude'] else None

                        # Check for duplicate regions
                        if state_id in processed_region_ids:
                            # self.stdout.write(self.style.ERROR(f'State {state_id} already processed'))
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
                                    # self.stdout.write(self.style.ERROR(f'City {city_id} already processed'))
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
            for i in tqdm(range(0, len(countries_to_create), batch_size), desc="Processing countries"):
                batch = countries_to_create[i:i + batch_size]
                Country.objects.bulk_create(batch)

            for i in tqdm(range(0, len(regions_to_create), batch_size), desc="Processing regions"):
                batch = regions_to_create[i:i + batch_size]
                Region.objects.bulk_create(batch)

            for i in tqdm(range(0, len(cities_to_create), batch_size), desc="Processing cities"):
                batch = cities_to_create[i:i + batch_size]
                City.objects.bulk_create(batch)

            # Process updates in batches
            for i in range(0, len(countries_to_update), batch_size):
                batch = countries_to_update[i:i + batch_size]
            for i in tqdm(range(0, len(countries_to_update), batch_size), desc="Updating countries"):
                batch = countries_to_update[i:i + batch_size]
                Country.objects.bulk_update(batch, ['name', 'subregion', 'capital', 'longitude', 'latitude'])

            for i in tqdm(range(0, len(regions_to_update), batch_size), desc="Updating regions"):
                batch = regions_to_update[i:i + batch_size]
                Region.objects.bulk_update(batch, ['name', 'country', 'longitude', 'latitude'])

            for i in tqdm(range(0, len(cities_to_update), batch_size), desc="Updating cities"):
                batch = cities_to_update[i:i + batch_size]
                City.objects.bulk_update(batch, ['name', 'region', 'longitude', 'latitude'])
            Country.objects.exclude(country_code__in=processed_country_codes).delete()
            Region.objects.exclude(id__in=processed_region_ids).delete()
            City.objects.exclude(id__in=processed_city_ids).delete()

        self.stdout.write(self.style.SUCCESS('All data imported successfully'))