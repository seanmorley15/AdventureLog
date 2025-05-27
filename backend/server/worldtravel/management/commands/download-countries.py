import os
from django.core.management.base import BaseCommand
import requests
from worldtravel.models import Country, Region, City
from django.db import transaction
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
        batch_size = 1000  # Larger batch size for better efficiency
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

        self.stdout.write(self.style.SUCCESS('Starting memory-efficient import process...'))

        # Pass 1: Process countries only
        self.stdout.write(self.style.WARNING('Pass 1: Processing countries...'))
        processed_country_codes = self._process_countries_pass(countries_json_path, batch_size)
        
        # Pass 2: Process regions only
        self.stdout.write(self.style.WARNING('Pass 2: Processing regions...'))
        processed_region_ids = self._process_regions_pass(countries_json_path, batch_size)
        
        # Pass 3: Process cities only
        self.stdout.write(self.style.WARNING('Pass 3: Processing cities...'))
        processed_city_ids = self._process_cities_pass(countries_json_path, batch_size)

        # Clean up obsolete records
        self.stdout.write(self.style.WARNING('Pass 4: Cleaning up obsolete records...'))
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

    def _process_countries_pass(self, json_path, batch_size):
        """First pass: Process only countries"""
        self.stdout.write('  Loading existing countries...')
        existing_countries = {c.country_code: c for c in Country.objects.all()}
        self.stdout.write(f'  Found {len(existing_countries)} existing countries')
        
        processed_country_codes = set()
        countries_to_create = []
        countries_to_update = []
        country_count = 0
        batches_processed = 0
        
        with open(json_path, 'rb') as f:
            parser = ijson.items(f, 'item')
            
            for country in parser:
                country_count += 1
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

                # Download flag
                saveCountryFlag(country_code)

                # Process in batches to limit memory usage
                if len(countries_to_create) >= batch_size or len(countries_to_update) >= batch_size:
                    batches_processed += 1
                    self.stdout.write(f'  Saving batch {batches_processed} ({len(countries_to_create)} new, {len(countries_to_update)} updated)')
                    self._flush_countries_batch(countries_to_create, countries_to_update, batch_size)
                    countries_to_create.clear()
                    countries_to_update.clear()
                    gc.collect()

                if country_count % 50 == 0:
                    self.stdout.write(f'  Processed {country_count} countries...')

            # Process remaining countries
            if countries_to_create or countries_to_update:
                batches_processed += 1
                self.stdout.write(f'  Saving final batch ({len(countries_to_create)} new, {len(countries_to_update)} updated)')
                self._flush_countries_batch(countries_to_create, countries_to_update, batch_size)

        self.stdout.write(self.style.SUCCESS(f'  ✓ Completed: {country_count} countries processed in {batches_processed} batches'))
        return processed_country_codes

    def _process_regions_pass(self, json_path, batch_size):
        """Second pass: Process only regions"""
        self.stdout.write('  Loading countries and existing regions...')
        existing_regions = {r.id: r for r in Region.objects.all()}
        countries_dict = {c.country_code: c for c in Country.objects.all()}
        self.stdout.write(f'  Found {len(existing_regions)} existing regions, {len(countries_dict)} countries')
        
        processed_region_ids = set()
        regions_to_create = []
        regions_to_update = []
        region_count = 0
        batches_processed = 0
        
        with open(json_path, 'rb') as f:
            parser = ijson.items(f, 'item')
            
            for country in parser:
                country_code = country['iso2']
                country_name = country['name']
                country_obj = countries_dict[country_code]
                
                if country['states']:
                    for state in country['states']:
                        name = state['name']
                        state_id = f"{country_code}-{state['state_code']}"
                        latitude = round(float(state['latitude']), 6) if state['latitude'] else None
                        longitude = round(float(state['longitude']), 6) if state['longitude'] else None

                        if state_id in processed_region_ids:
                            continue

                        processed_region_ids.add(state_id)
                        region_count += 1

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

                        # Process in batches
                        if len(regions_to_create) >= batch_size or len(regions_to_update) >= batch_size:
                            batches_processed += 1
                            self.stdout.write(f'  Saving batch {batches_processed} ({len(regions_to_create)} new, {len(regions_to_update)} updated)')
                            self._flush_regions_batch(regions_to_create, regions_to_update, batch_size)
                            regions_to_create.clear()
                            regions_to_update.clear()
                            gc.collect()
                else:
                    # Country without states - create a default region
                    state_id = f"{country_code}-00"
                    if state_id not in processed_region_ids:
                        processed_region_ids.add(state_id)
                        region_count += 1
                        
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

                if region_count % 2000 == 0 and region_count > 0:
                    self.stdout.write(f'  Processed {region_count} regions...')

            # Process remaining regions
            if regions_to_create or regions_to_update:
                batches_processed += 1
                self.stdout.write(f'  Saving final batch ({len(regions_to_create)} new, {len(regions_to_update)} updated)')
                self._flush_regions_batch(regions_to_create, regions_to_update, batch_size)

        self.stdout.write(self.style.SUCCESS(f'  ✓ Completed: {region_count} regions processed in {batches_processed} batches'))
        return processed_region_ids

    def _process_cities_pass(self, json_path, batch_size):
        """Third pass: Process only cities"""
        self.stdout.write('  Loading regions and existing cities...')
        existing_cities = {c.id: c for c in City.objects.all()}
        regions_dict = {r.id: r for r in Region.objects.all()}
        self.stdout.write(f'  Found {len(existing_cities)} existing cities, {len(regions_dict)} regions')
        
        processed_city_ids = set()
        cities_to_create = []
        cities_to_update = []
        city_count = 0
        batches_processed = 0
        
        with open(json_path, 'rb') as f:
            parser = ijson.items(f, 'item')
            
            for country in parser:
                country_code = country['iso2']
                
                if country['states']:
                    for state in country['states']:
                        state_id = f"{country_code}-{state['state_code']}"
                        region_obj = regions_dict.get(state_id)
                        
                        if not region_obj:
                            continue
                            
                        if 'cities' in state and len(state['cities']) > 0:
                            for city in state['cities']:
                                city_id = f"{state_id}-{city['id']}"
                                city_name = city['name']
                                latitude = round(float(city['latitude']), 6) if city['latitude'] else None
                                longitude = round(float(city['longitude']), 6) if city['longitude'] else None

                                if city_id in processed_city_ids:
                                    continue

                                processed_city_ids.add(city_id)
                                city_count += 1

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

                                # Process in batches
                                if len(cities_to_create) >= batch_size or len(cities_to_update) >= batch_size:
                                    batches_processed += 1
                                    self.stdout.write(f'  Saving batch {batches_processed} ({len(cities_to_create)} new, {len(cities_to_update)} updated)')
                                    self._flush_cities_batch(cities_to_create, cities_to_update, batch_size)
                                    cities_to_create.clear()
                                    cities_to_update.clear()
                                    gc.collect()

                if city_count % 10000 == 0 and city_count > 0:
                    self.stdout.write(f'  Processed {city_count} cities...')

            # Process remaining cities
            if cities_to_create or cities_to_update:
                batches_processed += 1
                self.stdout.write(f'  Saving final batch ({len(cities_to_create)} new, {len(cities_to_update)} updated)')
                self._flush_cities_batch(cities_to_create, cities_to_update, batch_size)

        self.stdout.write(self.style.SUCCESS(f'  ✓ Completed: {city_count} cities processed in {batches_processed} batches'))
        return processed_city_ids

    def _flush_countries_batch(self, countries_to_create, countries_to_update, batch_size):
        """Flush countries batch to database"""
        with transaction.atomic():
            if countries_to_create:
                for i in range(0, len(countries_to_create), batch_size):
                    batch = countries_to_create[i:i + batch_size]
                    Country.objects.bulk_create(batch, ignore_conflicts=True)

            if countries_to_update:
                for i in range(0, len(countries_to_update), batch_size):
                    batch = countries_to_update[i:i + batch_size]
                    Country.objects.bulk_update(batch, ['name', 'subregion', 'capital', 'longitude', 'latitude'])

    def _flush_regions_batch(self, regions_to_create, regions_to_update, batch_size):
        """Flush regions batch to database"""
        with transaction.atomic():
            if regions_to_create:
                for i in range(0, len(regions_to_create), batch_size):
                    batch = regions_to_create[i:i + batch_size]
                    Region.objects.bulk_create(batch, ignore_conflicts=True)

            if regions_to_update:
                for i in range(0, len(regions_to_update), batch_size):
                    batch = regions_to_update[i:i + batch_size]
                    Region.objects.bulk_update(batch, ['name', 'country', 'longitude', 'latitude'])

    def _flush_cities_batch(self, cities_to_create, cities_to_update, batch_size):
        """Flush cities batch to database"""
        with transaction.atomic():
            if cities_to_create:
                for i in range(0, len(cities_to_create), batch_size):
                    batch = cities_to_create[i:i + batch_size]
                    City.objects.bulk_create(batch, ignore_conflicts=True)

            if cities_to_update:
                for i in range(0, len(cities_to_update), batch_size):
                    batch = cities_to_update[i:i + batch_size]
                    City.objects.bulk_update(batch, ['name', 'region', 'longitude', 'latitude'])