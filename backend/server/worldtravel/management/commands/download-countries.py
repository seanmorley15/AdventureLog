import os
from django.core.management.base import BaseCommand
import requests
from worldtravel.models import Country, Region, City
from django.db import transaction
import ijson
import gc
import tempfile
import sqlite3
from contextlib import contextmanager

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
    help = 'Imports the world travel data with minimal memory usage'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force download the countries+regions+states.json file')
        parser.add_argument('--batch-size', type=int, default=500, help='Batch size for database operations')

    @contextmanager
    def _temp_db(self):
        """Create a temporary SQLite database for intermediate storage"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_db_path = f.name
        
        try:
            conn = sqlite3.connect(temp_db_path)
            conn.execute('''CREATE TABLE temp_countries (
                country_code TEXT PRIMARY KEY,
                name TEXT,
                subregion TEXT,
                capital TEXT,
                longitude REAL,
                latitude REAL
            )''')
            
            conn.execute('''CREATE TABLE temp_regions (
                id TEXT PRIMARY KEY,
                name TEXT,
                country_code TEXT,
                longitude REAL,
                latitude REAL
            )''')
            
            conn.execute('''CREATE TABLE temp_cities (
                id TEXT PRIMARY KEY,
                name TEXT,
                region_id TEXT,
                longitude REAL,
                latitude REAL
            )''')
            
            conn.commit()
            yield conn
        finally:
            conn.close()
            try:
                os.unlink(temp_db_path)
            except OSError:
                pass

    def handle(self, **options):
        force = options['force']
        batch_size = options['batch_size']
        countries_json_path = os.path.join(settings.MEDIA_ROOT, f'countries+regions+states-{COUNTRY_REGION_JSON_VERSION}.json')
        
        # Download or validate JSON file
        if not os.path.exists(countries_json_path) or force:
            self.stdout.write('Downloading JSON file...')
            res = requests.get(f'https://raw.githubusercontent.com/dr5hn/countries-states-cities-database/{COUNTRY_REGION_JSON_VERSION}/json/countries%2Bstates%2Bcities.json')
            if res.status_code == 200:
                with open(countries_json_path, 'w') as f:
                    f.write(res.text)
                self.stdout.write(self.style.SUCCESS('JSON file downloaded successfully'))
            else:
                self.stdout.write(self.style.ERROR('Error downloading JSON file'))
                return
        elif not os.path.isfile(countries_json_path):
            self.stdout.write(self.style.ERROR('JSON file is not a file'))
            return
        elif os.path.getsize(countries_json_path) == 0:
            self.stdout.write(self.style.ERROR('JSON file is empty'))
            return
        elif Country.objects.count() == 0 or Region.objects.count() == 0 or City.objects.count() == 0:
            self.stdout.write(self.style.WARNING('Some data is missing. Re-importing all data.'))
        else:
            self.stdout.write(self.style.SUCCESS('Latest data already imported.'))
            return

        self.stdout.write(self.style.SUCCESS('Starting ultra-memory-efficient import process...'))

        # Use temporary SQLite database for intermediate storage
        with self._temp_db() as temp_conn:
            self.stdout.write('Step 1: Parsing JSON and storing in temporary database...')
            self._parse_and_store_temp(countries_json_path, temp_conn)
            
            self.stdout.write('Step 2: Processing countries...')
            self._process_countries_from_temp(temp_conn, batch_size)
            
            self.stdout.write('Step 3: Processing regions...')  
            self._process_regions_from_temp(temp_conn, batch_size)
            
            self.stdout.write('Step 4: Processing cities...')
            self._process_cities_from_temp(temp_conn, batch_size)
            
            self.stdout.write('Step 5: Cleaning up obsolete records...')
            self._cleanup_obsolete_records(temp_conn)

        self.stdout.write(self.style.SUCCESS('All data imported successfully with minimal memory usage'))

    def _parse_and_store_temp(self, json_path, temp_conn):
        """Parse JSON once and store in temporary SQLite database"""
        country_count = 0
        region_count = 0
        city_count = 0
        
        with open(json_path, 'rb') as f:
            parser = ijson.items(f, 'item')
            
            for country in parser:
                country_code = country['iso2']
                country_name = country['name']
                country_subregion = country['subregion']
                country_capital = country['capital']
                longitude = round(float(country['longitude']), 6) if country['longitude'] else None
                latitude = round(float(country['latitude']), 6) if country['latitude'] else None

                # Store country
                temp_conn.execute('''INSERT OR REPLACE INTO temp_countries 
                    (country_code, name, subregion, capital, longitude, latitude) 
                    VALUES (?, ?, ?, ?, ?, ?)''',
                    (country_code, country_name, country_subregion, country_capital, longitude, latitude))
                
                country_count += 1
                
                # Download flag (do this during parsing to avoid extra pass)
                saveCountryFlag(country_code)

                # Process regions/states
                if country['states']:
                    for state in country['states']:
                        state_id = f"{country_code}-{state['state_code']}"
                        state_name = state['name']
                        state_lat = round(float(state['latitude']), 6) if state['latitude'] else None
                        state_lng = round(float(state['longitude']), 6) if state['longitude'] else None
                        
                        temp_conn.execute('''INSERT OR REPLACE INTO temp_regions 
                            (id, name, country_code, longitude, latitude) 
                            VALUES (?, ?, ?, ?, ?)''',
                            (state_id, state_name, country_code, state_lng, state_lat))
                        
                        region_count += 1
                        
                        # Process cities
                        if 'cities' in state and state['cities']:
                            for city in state['cities']:
                                city_id = f"{state_id}-{city['id']}"
                                city_name = city['name']
                                city_lat = round(float(city['latitude']), 6) if city['latitude'] else None
                                city_lng = round(float(city['longitude']), 6) if city['longitude'] else None
                                
                                temp_conn.execute('''INSERT OR REPLACE INTO temp_cities 
                                    (id, name, region_id, longitude, latitude) 
                                    VALUES (?, ?, ?, ?, ?)''',
                                    (city_id, city_name, state_id, city_lng, city_lat))
                                
                                city_count += 1
                else:
                    # Country without states - create default region
                    state_id = f"{country_code}-00"
                    temp_conn.execute('''INSERT OR REPLACE INTO temp_regions 
                        (id, name, country_code, longitude, latitude) 
                        VALUES (?, ?, ?, ?, ?)''',
                        (state_id, country_name, country_code, None, None))
                    region_count += 1

                # Commit periodically to avoid memory buildup
                if country_count % 100 == 0:
                    temp_conn.commit()
                    self.stdout.write(f'  Parsed {country_count} countries, {region_count} regions, {city_count} cities...')

        temp_conn.commit()
        self.stdout.write(f'✓ Parsing complete: {country_count} countries, {region_count} regions, {city_count} cities')

    def _process_countries_from_temp(self, temp_conn, batch_size):
        """Process countries from temporary database"""
        cursor = temp_conn.execute('SELECT country_code, name, subregion, capital, longitude, latitude FROM temp_countries')
        
        countries_to_create = []
        countries_to_update = []
        processed = 0
        
        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
                
            # Batch check for existing countries
            country_codes_in_batch = [row[0] for row in rows]
            existing_countries = {
                c.country_code: c for c in 
                Country.objects.filter(country_code__in=country_codes_in_batch)
                .only('country_code', 'name', 'subregion', 'capital', 'longitude', 'latitude')
            }
            
            for row in rows:
                country_code, name, subregion, capital, longitude, latitude = row
                
                if country_code in existing_countries:
                    # Update existing
                    country_obj = existing_countries[country_code]
                    country_obj.name = name
                    country_obj.subregion = subregion
                    country_obj.capital = capital
                    country_obj.longitude = longitude
                    country_obj.latitude = latitude
                    countries_to_update.append(country_obj)
                else:
                    countries_to_create.append(Country(
                        country_code=country_code,
                        name=name,
                        subregion=subregion,
                        capital=capital,
                        longitude=longitude,
                        latitude=latitude
                    ))
                
                processed += 1
                
            # Flush batches
            if countries_to_create:
                with transaction.atomic():
                    Country.objects.bulk_create(countries_to_create, batch_size=batch_size, ignore_conflicts=True)
                countries_to_create.clear()
                
            if countries_to_update:
                with transaction.atomic():
                    Country.objects.bulk_update(
                        countries_to_update, 
                        ['name', 'subregion', 'capital', 'longitude', 'latitude'],
                        batch_size=batch_size
                    )
                countries_to_update.clear()
                
            if processed % 1000 == 0:
                self.stdout.write(f'  Processed {processed} countries...')
                gc.collect()
        
        # Final flush
        if countries_to_create:
            with transaction.atomic():
                Country.objects.bulk_create(countries_to_create, batch_size=batch_size, ignore_conflicts=True)
        if countries_to_update:
            with transaction.atomic():
                Country.objects.bulk_update(
                    countries_to_update, 
                    ['name', 'subregion', 'capital', 'longitude', 'latitude'],
                    batch_size=batch_size
                )
        
        self.stdout.write(f'✓ Countries complete: {processed} processed')

    def _process_regions_from_temp(self, temp_conn, batch_size):
        """Process regions from temporary database"""
        # Get country mapping once
        country_map = {c.country_code: c for c in Country.objects.only('id', 'country_code')}
        
        cursor = temp_conn.execute('SELECT id, name, country_code, longitude, latitude FROM temp_regions')
        
        regions_to_create = []
        regions_to_update = []
        processed = 0
        
        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
                
            # Batch check for existing regions
            region_ids_in_batch = [row[0] for row in rows]
            existing_regions = {
                r.id: r for r in 
                Region.objects.filter(id__in=region_ids_in_batch)
                .select_related('country')
                .only('id', 'name', 'country', 'longitude', 'latitude')
            }
            
            for row in rows:
                region_id, name, country_code, longitude, latitude = row
                country_obj = country_map.get(country_code)
                
                if not country_obj:
                    continue
                    
                if region_id in existing_regions:
                    # Update existing
                    region_obj = existing_regions[region_id]
                    region_obj.name = name
                    region_obj.country = country_obj
                    region_obj.longitude = longitude
                    region_obj.latitude = latitude
                    regions_to_update.append(region_obj)
                else:
                    regions_to_create.append(Region(
                        id=region_id,
                        name=name,
                        country=country_obj,
                        longitude=longitude,
                        latitude=latitude
                    ))
                
                processed += 1
                
            # Flush batches
            if regions_to_create:
                with transaction.atomic():
                    Region.objects.bulk_create(regions_to_create, batch_size=batch_size, ignore_conflicts=True)
                regions_to_create.clear()
                
            if regions_to_update:
                with transaction.atomic():
                    Region.objects.bulk_update(
                        regions_to_update, 
                        ['name', 'country', 'longitude', 'latitude'],
                        batch_size=batch_size
                    )
                regions_to_update.clear()
                
            if processed % 2000 == 0:
                self.stdout.write(f'  Processed {processed} regions...')
                gc.collect()
        
        # Final flush
        if regions_to_create:
            with transaction.atomic():
                Region.objects.bulk_create(regions_to_create, batch_size=batch_size, ignore_conflicts=True)
        if regions_to_update:
            with transaction.atomic():
                Region.objects.bulk_update(
                    regions_to_update, 
                    ['name', 'country', 'longitude', 'latitude'],
                    batch_size=batch_size
                )
        
        self.stdout.write(f'✓ Regions complete: {processed} processed')

    def _process_cities_from_temp(self, temp_conn, batch_size):
        """Process cities from temporary database with optimized existence checking"""
        # Get region mapping once
        region_map = {r.id: r for r in Region.objects.only('id')}
        
        cursor = temp_conn.execute('SELECT id, name, region_id, longitude, latitude FROM temp_cities')
        
        cities_to_create = []
        cities_to_update = []
        processed = 0
        
        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
                
            # Fast existence check - only get IDs, no objects
            city_ids_in_batch = [row[0] for row in rows]
            existing_city_ids = set(
                City.objects.filter(id__in=city_ids_in_batch)
                .values_list('id', flat=True)
            )
            
            for row in rows:
                city_id, name, region_id, longitude, latitude = row
                region_obj = region_map.get(region_id)
                
                if not region_obj:
                    continue
                    
                if city_id in existing_city_ids:
                    # For updates, just store the data - we'll do bulk update by raw SQL
                    cities_to_update.append({
                        'id': city_id,
                        'name': name,
                        'region_id': region_obj.id,
                        'longitude': longitude,
                        'latitude': latitude
                    })
                else:
                    cities_to_create.append(City(
                        id=city_id,
                        name=name,
                        region=region_obj,
                        longitude=longitude,
                        latitude=latitude
                    ))
                
                processed += 1
                
            # Flush create batch (this is already fast)
            if cities_to_create:
                with transaction.atomic():
                    City.objects.bulk_create(cities_to_create, batch_size=batch_size, ignore_conflicts=True)
                cities_to_create.clear()
                
            # Flush update batch with raw SQL for speed
            if cities_to_update:
                self._bulk_update_cities_raw(cities_to_update)
                cities_to_update.clear()
                
            if processed % 5000 == 0:
                self.stdout.write(f'  Processed {processed} cities...')
                gc.collect()
        
        # Final flush
        if cities_to_create:
            with transaction.atomic():
                City.objects.bulk_create(cities_to_create, batch_size=batch_size, ignore_conflicts=True)
        if cities_to_update:
            self._bulk_update_cities_raw(cities_to_update)
        
        self.stdout.write(f'✓ Cities complete: {processed} processed')

    def _bulk_update_cities_raw(self, cities_data):
        """Fast bulk update using raw SQL"""
        if not cities_data:
            return
            
        from django.db import connection
        
        with connection.cursor() as cursor:
            # Build the SQL for bulk update
            # Using CASE statements for efficient bulk updates
            when_clauses_name = []
            when_clauses_region = []
            when_clauses_lng = []
            when_clauses_lat = []
            city_ids = []
            
            for city in cities_data:
                city_id = city['id']
                city_ids.append(city_id)
                when_clauses_name.append(f"WHEN id = %s THEN %s")
                when_clauses_region.append(f"WHEN id = %s THEN %s")
                when_clauses_lng.append(f"WHEN id = %s THEN %s")
                when_clauses_lat.append(f"WHEN id = %s THEN %s")
            
            # Build parameters list
            params = []
            for city in cities_data:
                params.extend([city['id'], city['name']])  # for name
            for city in cities_data:
                params.extend([city['id'], city['region_id']])  # for region_id
            for city in cities_data:
                params.extend([city['id'], city['longitude']])  # for longitude
            for city in cities_data:
                params.extend([city['id'], city['latitude']])  # for latitude
            params.extend(city_ids)  # for WHERE clause
            
            # Execute the bulk update
            sql = f"""
                UPDATE worldtravel_city 
                SET 
                    name = CASE {' '.join(when_clauses_name)} END,
                    region_id = CASE {' '.join(when_clauses_region)} END,
                    longitude = CASE {' '.join(when_clauses_lng)} END,
                    latitude = CASE {' '.join(when_clauses_lat)} END
                WHERE id IN ({','.join(['%s'] * len(city_ids))})
            """
            
            cursor.execute(sql, params)

    def _cleanup_obsolete_records(self, temp_conn):
        """Clean up obsolete records using temporary database"""
        # Get IDs from temp database to avoid loading large lists into memory
        temp_country_codes = {row[0] for row in temp_conn.execute('SELECT country_code FROM temp_countries')}
        temp_region_ids = {row[0] for row in temp_conn.execute('SELECT id FROM temp_regions')}
        temp_city_ids = {row[0] for row in temp_conn.execute('SELECT id FROM temp_cities')}
        
        with transaction.atomic():
            countries_deleted = Country.objects.exclude(country_code__in=temp_country_codes).count()
            regions_deleted = Region.objects.exclude(id__in=temp_region_ids).count()
            cities_deleted = City.objects.exclude(id__in=temp_city_ids).count()
            
            Country.objects.exclude(country_code__in=temp_country_codes).delete()
            Region.objects.exclude(id__in=temp_region_ids).delete()
            City.objects.exclude(id__in=temp_city_ids).delete()
            
            if countries_deleted > 0 or regions_deleted > 0 or cities_deleted > 0:
                self.stdout.write(f'✓ Deleted {countries_deleted} obsolete countries, {regions_deleted} regions, {cities_deleted} cities')
            else:
                self.stdout.write('✓ No obsolete records found to delete')