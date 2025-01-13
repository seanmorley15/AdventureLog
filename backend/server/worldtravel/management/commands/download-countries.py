import os
import requests
import uuid
from django.core.management.base import BaseCommand
from worldtravel.models import Country, Region, City
from django.db import transaction
import ijson
from django.conf import settings
import psutil

def get_memory_usage():
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    return memory_info.rss  # in bytes

def log_memory_usage(stage):
    memory_usage = get_memory_usage()
    print(f"Memory usage at {stage}: {memory_usage / 1024 / 1024:.2f} MB")

COUNTRY_REGION_JSON_VERSION = settings.COUNTRY_REGION_JSON_VERSION
media_root = settings.MEDIA_ROOT

def saveCountryFlag(country_code):
    country_code = country_code.lower()
    flags_dir = os.path.join(media_root, 'flags')
    if not os.path.exists(flags_dir):
        os.makedirs(flags_dir)

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
        log_memory_usage("start")
        force = options['force']
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
        
        insert_id = uuid.uuid4()
            
        with transaction.atomic():
            f = open(countries_json_path, 'rb')
            parser = ijson.items(f, 'item')

            region_batch = []
            city_batch = []
            existing_region_ids = set()
            existing_city_ids = set()

            for country in parser:
                country_code = country['iso2']
                country_name = country['name']
                country_subregion = country['subregion']
                country_capital = country['capital']
                longitude = round(float(country['longitude']), 6) if country['longitude'] else None
                latitude = round(float(country['latitude']), 6) if country['latitude'] else None

                country_obj, _ = Country.objects.update_or_create(
                    country_code=country_code,
                    defaults={ 
                        'name': country_name,
                        'subregion': country_subregion,
                        'capital': country_capital,
                        'longitude': longitude,
                        'latitude': latitude,
                        'insert_id': insert_id
                    }
                )

                saveCountryFlag(country_code)
                log_memory_usage(country_code)

            if country['states']:
                for state in country['states']:
                    state_id = f"{country_code}-{state['state_code']}" if state['state_code'] else f"{country_code}-00"
                    
                    # Ensure no duplicate regions
                    if state_id not in existing_region_ids:
                        region_obj = Region(
                            id=state_id,
                            name=state['name'],
                            country=country_obj,
                            longitude=state['longitude'],
                            latitude=state['latitude'],
                            insert_id=insert_id
                        )
                        region_batch.append(region_obj)
                        existing_region_ids.add(state_id)
                        log_memory_usage(state_id)

                    # Handle cities and avoid duplicates
                    if 'cities' in state and len(state['cities']) > 0:
                        for city in state['cities']:
                            city_id = f"{state_id}-{city['id']}"
                            
                            if city_id not in existing_city_ids:
                                city_obj = City(
                                    id=city_id,
                                    name=city['name'],
                                    region=region_obj,
                                    longitude=city['longitude'],
                                    latitude=city['latitude'],
                                    insert_id=insert_id
                                )
                                city_batch.append(city_obj)
                                existing_city_ids.add(city_id)

            # Bulk insert regions in smaller batches
            if len(region_batch) >= 100:
                Region.objects.bulk_create(
                    region_batch,
                    update_conflicts=True,
                    batch_size=100,
                    update_fields=['name', 'country', 'longitude', 'latitude', 'insert_id'],
                    unique_fields=['id']
                )
                region_batch.clear()

            # Bulk insert cities in smaller batches
            if len(city_batch) >= 100:
                City.objects.bulk_create(
                    city_batch,
                    update_conflicts=True,
                    batch_size=100,
                    update_fields=['name', 'region', 'longitude', 'latitude', 'insert_id'],
                    unique_fields=['id']
                )
                city_batch.clear()

        # Final insertion of any remaining regions and cities
        if region_batch:
            Region.objects.bulk_create(
                region_batch,
                update_conflicts=True,
                batch_size=100,
                update_fields=['name', 'country', 'longitude', 'latitude', 'insert_id'],
                unique_fields=['id']
            )

        if city_batch:
            City.objects.bulk_create(
                city_batch,
                update_conflicts=True,
                batch_size=100,
                update_fields=['name', 'region', 'longitude', 'latitude', 'insert_id'],
                unique_fields=['id']
            )

        self.stdout.write(self.style.SUCCESS('Regions and cities created'))

        # Clean up old data
        Country.objects.exclude(insert_id=insert_id).delete()
        Region.objects.exclude(insert_id=insert_id).delete()
        City.objects.exclude(insert_id=insert_id).delete()

        self.stdout.write(self.style.SUCCESS('All data imported successfully and old data cleaned up'))