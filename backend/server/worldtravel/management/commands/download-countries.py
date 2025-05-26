import os
from django.core.management.base import BaseCommand
import requests
from worldtravel.models import Country, Region, City
from django.db import transaction
from tqdm import tqdm
import ijson
import gc

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
        batch_size = 500  # Increased batch size for better performance
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
            return
        elif Country.objects.count() == 0 or Region.objects.count() == 0 or City.objects.count() == 0:
            self.stdout.write(self.style.WARNING('Some region data is missing. Re-importing all data.'))
        else:
            self.stdout.write(self.style.SUCCESS('Latest country, region, and state data already downloaded.'))
            return

        # Use sets for faster lookup instead of dictionaries when we only need existence checks
        self.stdout.write(self.style.SUCCESS('Loading existing data for comparison...'))
        existing_country_codes = set(Country.objects.values_list('country_code', flat=True))
        existing_region_ids = set(Region.objects.values_list('id', flat=True))
        existing_city_ids = set(City.objects.values_list('id', flat=True))
        
        self.stdout.write(self.style.SUCCESS(f'Found {len(existing_country_codes)} existing countries, {len(existing_region_ids)} regions, {len(existing_city_ids)} cities'))

        # Only fetch full objects when we actually need to update them
        existing_countries = {}
        existing_regions = {}
        existing_cities = {}

        processed_country_codes = set()
        processed_region_ids = set()
        processed_city_ids = set()

        # Process data in streaming fashion to avoid loading everything into memory
        self.stdout.write(self.style.SUCCESS('Starting to process country data...'))
        with open(countries_json_path, 'rb') as f:
            parser = ijson.items(f, 'item')
            
            countries_to_create = []
            regions_to_create = []
            cities_to_create = []
            
            countries_to_update = []
            regions_to_update = []
            cities_to_update = []

            country_count = 0
            total_regions_processed = 0
            total_cities_processed = 0
            batch_number = 1
            
            for country in parser:
                country_count += 1
                country_code = country['iso2']
                country_name = country['name']
                country_subregion = country['subregion']
                country_capital = country['capital']
                longitude = round(float(country['longitude']), 6) if country['longitude'] else None
                latitude = round(float(country['latitude']), 6) if country['latitude'] else None

                if country_count % 10 == 0:
                    self.stdout.write(f'Processing country {country_count}: {country_name} ({country_code})')

                processed_country_codes.add(country_code)

                if country_code in existing_country_codes:
                    # Only fetch when needed for updates
                    if country_code not in existing_countries:
                        existing_countries[country_code] = Country.objects.get(country_code=country_code)
                    
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

                # Process states/regions
                region_count_for_country = 0
                city_count_for_country = 0
                
                if country['states']:
                    for state in country['states']:
                        name = state['name']
                        state_id = f"{country_code}-{state['state_code']}"
                        latitude = round(float(state['latitude']), 6) if state['latitude'] else None
                        longitude = round(float(state['longitude']), 6) if state['longitude'] else None

                        if state_id in processed_region_ids:
                            continue

                        processed_region_ids.add(state_id)
                        region_count_for_country += 1
                        total_regions_processed += 1

                        if state_id in existing_region_ids:
                            if state_id not in existing_regions:
                                existing_regions[state_id] = Region.objects.get(id=state_id)
                            
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

                        # Process cities
                        if 'cities' in state and len(state['cities']) > 0:
                            for city in state['cities']:
                                city_id = f"{state_id}-{city['id']}"
                                city_name = city['name']
                                latitude = round(float(city['latitude']), 6) if city['latitude'] else None
                                longitude = round(float(city['longitude']), 6) if city['longitude'] else None

                                if city_id in processed_city_ids:
                                    continue

                                processed_city_ids.add(city_id)
                                city_count_for_country += 1
                                total_cities_processed += 1

                                if city_id in existing_city_ids:
                                    if city_id not in existing_cities:
                                        existing_cities[city_id] = City.objects.get(id=city_id)
                                    
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
                else:
                    # Country without states - create a default region
                    state_id = f"{country_code}-00"
                    processed_region_ids.add(state_id)
                    region_count_for_country = 1
                    total_regions_processed += 1
                    
                    if state_id in existing_region_ids:
                        if state_id not in existing_regions:
                            existing_regions[state_id] = Region.objects.get(id=state_id)
                        
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

                if country_count % 10 == 0:
                    self.stdout.write(f'  └─ {country_name}: {region_count_for_country} regions, {city_count_for_country} cities')

                # Process in batches during iteration to manage memory
                if country_count % 50 == 0:  # Process every 50 countries
                    self.stdout.write(self.style.WARNING(f'Processing batch {batch_number} (countries {country_count-49}-{country_count})...'))
                    self.stdout.write(f'  Countries to create: {len(countries_to_create)}, to update: {len(countries_to_update)}')
                    self.stdout.write(f'  Regions to create: {len(regions_to_create)}, to update: {len(regions_to_update)}')
                    self.stdout.write(f'  Cities to create: {len(cities_to_create)}, to update: {len(cities_to_update)}')
                    
                    self._process_batches(
                        countries_to_create, regions_to_create, cities_to_create,
                        countries_to_update, regions_to_update, cities_to_update,
                        batch_size
                    )
                    
                    self.stdout.write(self.style.SUCCESS(f'✓ Batch {batch_number} completed successfully'))
                    
                    # Clear processed batches and force garbage collection
                    countries_to_create.clear()
                    regions_to_create.clear()
                    cities_to_create.clear()
                    countries_to_update.clear()
                    regions_to_update.clear()
                    cities_to_update.clear()
                    
                    # Clear the cached objects to free memory
                    existing_countries.clear()
                    existing_regions.clear()
                    existing_cities.clear()
                    
                    gc.collect()
                    batch_number += 1

            # Process remaining batches
            if countries_to_create or regions_to_create or cities_to_create or \
               countries_to_update or regions_to_update or cities_to_update:
                self.stdout.write(self.style.WARNING(f'Processing final batch {batch_number} (remaining {len(countries_to_create + countries_to_update)} countries)...'))
                self.stdout.write(f'  Countries to create: {len(countries_to_create)}, to update: {len(countries_to_update)}')
                self.stdout.write(f'  Regions to create: {len(regions_to_create)}, to update: {len(regions_to_update)}')
                self.stdout.write(f'  Cities to create: {len(cities_to_create)}, to update: {len(cities_to_update)}')
                
                self._process_batches(
                    countries_to_create, regions_to_create, cities_to_create,
                    countries_to_update, regions_to_update, cities_to_update,
                    batch_size
                )
                self.stdout.write(self.style.SUCCESS(f'✓ Final batch completed successfully'))

        self.stdout.write(self.style.SUCCESS(f'Finished processing {country_count} countries, {total_regions_processed} regions, {total_cities_processed} cities'))

        # Clean up obsolete records
        self.stdout.write(self.style.WARNING('Cleaning up obsolete records...'))
        with transaction.atomic():
            countries_deleted = Country.objects.exclude(country_code__in=processed_country_codes).count()
            regions_deleted = Region.objects.exclude(id__in=processed_region_ids).count() 
            cities_deleted = City.objects.exclude(id__in=processed_city_ids).count()
            
            Country.objects.exclude(country_code__in=processed_country_codes).delete()
            Region.objects.exclude(id__in=processed_region_ids).delete()
            City.objects.exclude(id__in=processed_city_ids).delete()
            
            if countries_deleted > 0 or regions_deleted > 0 or cities_deleted > 0:
                self.stdout.write(f'  Deleted {countries_deleted} obsolete countries, {regions_deleted} regions, {cities_deleted} cities')
            else:
                self.stdout.write('  No obsolete records found to delete')

        self.stdout.write(self.style.SUCCESS('All data imported successfully'))

    def _process_batches(self, countries_to_create, regions_to_create, cities_to_create,
                        countries_to_update, regions_to_update, cities_to_update, batch_size):
        """Process all pending batches in a single transaction"""
        with transaction.atomic():
            # Create new records
            if countries_to_create:
                self.stdout.write(f'    Creating {len(countries_to_create)} countries in batches of {batch_size}...')
                for i in range(0, len(countries_to_create), batch_size):
                    batch = countries_to_create[i:i + batch_size]
                    Country.objects.bulk_create(batch, ignore_conflicts=True)

            if regions_to_create:
                self.stdout.write(f'    Creating {len(regions_to_create)} regions in batches of {batch_size}...')
                for i in range(0, len(regions_to_create), batch_size):
                    batch = regions_to_create[i:i + batch_size]
                    Region.objects.bulk_create(batch, ignore_conflicts=True)

            if cities_to_create:
                self.stdout.write(f'    Creating {len(cities_to_create)} cities in batches of {batch_size}...')
                for i in range(0, len(cities_to_create), batch_size):
                    batch = cities_to_create[i:i + batch_size]
                    City.objects.bulk_create(batch, ignore_conflicts=True)

            # Update existing records
            if countries_to_update:
                self.stdout.write(f'    Updating {len(countries_to_update)} countries in batches of {batch_size}...')
                for i in range(0, len(countries_to_update), batch_size):
                    batch = countries_to_update[i:i + batch_size]
                    Country.objects.bulk_update(batch, ['name', 'subregion', 'capital', 'longitude', 'latitude'])

            if regions_to_update:
                self.stdout.write(f'    Updating {len(regions_to_update)} regions in batches of {batch_size}...')
                for i in range(0, len(regions_to_update), batch_size):
                    batch = regions_to_update[i:i + batch_size]
                    Region.objects.bulk_update(batch, ['name', 'country', 'longitude', 'latitude'])

            if cities_to_update:
                self.stdout.write(f'    Updating {len(cities_to_update)} cities in batches of {batch_size}...')
                for i in range(0, len(cities_to_update), batch_size):
                    batch = cities_to_update[i:i + batch_size]
                    City.objects.bulk_update(batch, ['name', 'region', 'longitude', 'latitude'])