import os
from django.core.management.base import BaseCommand
import requests
from worldtravel.models import Country, Region, City, CityAlias, VisitedCity
from django.db import transaction
import ijson
import gc
import tempfile
import sqlite3
from contextlib import contextmanager
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from django.conf import settings
from core.geo import distance_km, make_point, parse_lon_lat
from worldtravel.territories import find_territory_links, pair_cities

COUNTRY_REGION_JSON_VERSION = settings.COUNTRY_REGION_JSON_VERSION

# A city listed under a region that is also a country moves to the nearest region of that country,
# if one is this close. A city with no usable position stays where the dataset put it.
NEAREST_REGION_KM = 100


def coordinates_from_lon_lat(longitude, latitude):
    if longitude is None or latitude is None:
        return None
    return make_point(longitude, latitude)

def save_country_flag(country_code):
    # For standards, use the lowercase country_code
    country_code = country_code.lower()
    flag_path = f"flags/{country_code}.png"

    # Check if the flag already exists in storage
    if default_storage.exists(flag_path):
        print(f'Flag for {country_code} already exists')
        return

    res = requests.get(f'https://flagcdn.com/h240/{country_code}.png'.lower())
    if res.status_code == 200:
        default_storage.save(flag_path, ContentFile(res.content))
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
                native TEXT,
                subregion TEXT,
                capital TEXT,
                longitude REAL,
                latitude REAL
            )''')
            
            conn.execute('''CREATE TABLE temp_regions (
                id TEXT PRIMARY KEY,
                name TEXT,
                native TEXT,
                type TEXT,
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
            
            conn.execute('''CREATE TABLE temp_city_aliases (
                old_id TEXT PRIMARY KEY,
                new_id TEXT
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
        countries_json_path = f'countries+regions+states-{COUNTRY_REGION_JSON_VERSION}.json'
        
        # Download or validate JSON file
        if not default_storage.exists(countries_json_path) or force:
            self.stdout.write('Downloading JSON file...')
            if force and default_storage.exists(countries_json_path):
                default_storage.delete(countries_json_path)
            res = requests.get(f'https://raw.githubusercontent.com/dr5hn/countries-states-cities-database/{COUNTRY_REGION_JSON_VERSION}/json/countries%2Bstates%2Bcities.json')
            if res.status_code == 200:
                default_storage.save(countries_json_path, ContentFile(res.content))
                self.stdout.write(self.style.SUCCESS('JSON file downloaded successfully'))
            else:
                self.stdout.write(self.style.ERROR('Error downloading JSON file'))
                return
        elif default_storage.size(countries_json_path) == 0:
            self.stdout.write(self.style.ERROR('JSON file is empty'))
            return
        elif Country.objects.count() == 0 or Region.objects.count() == 0 or City.objects.count() == 0:
            self.stdout.write(self.style.WARNING('Some data is missing. Re-importing all data.'))
        elif Country.objects.filter(native_name__isnull=True).exists():
            # Rows from before native names and territory links were stored. Missing names
            # are stored as '' so this runs once.
            self.stdout.write(self.style.WARNING('Native names and territory links are missing. Re-importing all data.'))
        else:
            self.stdout.write(self.style.SUCCESS('Latest data already imported.'))
            return

        self.stdout.write(self.style.SUCCESS('Starting ultra-memory-efficient import process...'))

        # Use temporary SQLite database for intermediate storage
        with self._temp_db() as temp_conn:
            self.stdout.write('Step 1: Parsing JSON and storing in temporary database...')
            self._parse_and_store_temp(countries_json_path, temp_conn)
            
            self.stdout.write('Step 1b: Merging cities listed under a region that is also a country...')
            self._merge_territory_cities(temp_conn)

            self.stdout.write('Step 2: Processing countries...')
            self._process_countries_from_temp(temp_conn, batch_size)
            
            self.stdout.write('Step 3: Processing regions...')  
            self._process_regions_from_temp(temp_conn, batch_size)

            self.stdout.write('Step 3b: Linking regions that are also countries...')
            self._link_territories(temp_conn)
            
            self.stdout.write('Step 4: Processing cities...')
            self._process_cities_from_temp(temp_conn, batch_size)
            
            self.stdout.write('Step 4b: Pointing places at the cities they were merged into...')
            self._remap_merged_cities(temp_conn)

            self.stdout.write('Step 5: Cleaning up obsolete records...')
            self._cleanup_obsolete_records(temp_conn)

        self.stdout.write(self.style.SUCCESS('All data imported successfully with minimal memory usage'))

    def _parse_and_store_temp(self, json_path, temp_conn):
        """Parse JSON once and store in temporary SQLite database"""
        country_count = 0
        region_count = 0
        city_count = 0
        
        with default_storage.open(json_path, 'rb') as f:
            parser = ijson.items(f, 'item')
            
            for country in parser:
                country_code = country['iso2']
                country_name = country['name']
                country_native = country.get('native') or ''
                country_subregion = country['subregion']
                country_capital = country['capital']
                longitude, latitude = parse_lon_lat(country.get('longitude'), country.get('latitude'))

                # Store country
                temp_conn.execute('''INSERT OR REPLACE INTO temp_countries 
                    (country_code, name, native, subregion, capital, longitude, latitude) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (country_code, country_name, country_native, country_subregion, country_capital, longitude, latitude))
                
                country_count += 1
                
                # Download flag (do this during parsing to avoid extra pass)
                save_country_flag(country_code)

                # Process regions/states
                if country['states']:
                    for state in country['states']:
                        state_id = f"{country_code}-{state['iso2']}"
                        state_name = state['name']
                        state_lng, state_lat = parse_lon_lat(state.get('longitude'), state.get('latitude'))
                        if state_lng is None or state_lat is None:
                            state_lng, state_lat = longitude, latitude
                        
                        temp_conn.execute('''INSERT OR REPLACE INTO temp_regions 
                            (id, name, native, type, country_code, longitude, latitude) 
                            VALUES (?, ?, ?, ?, ?, ?, ?)''',
                            (state_id, state_name, state.get('native') or '', state.get('type') or '',
                             country_code, state_lng, state_lat))
                        
                        region_count += 1
                        
                        # Process cities
                        if 'cities' in state and state['cities']:
                            for city in state['cities']:
                                city_id = f"{state_id}-{city['id']}"
                                city_name = city['name']
                                city_lng, city_lat = parse_lon_lat(city.get('longitude'), city.get('latitude'))
                                
                                temp_conn.execute('''INSERT OR REPLACE INTO temp_cities 
                                    (id, name, region_id, longitude, latitude) 
                                    VALUES (?, ?, ?, ?, ?)''',
                                    (city_id, city_name, state_id, city_lng, city_lat))
                                
                                city_count += 1
                else:
                    # Country without states (city-states, etc.) — one region at the country centroid
                    state_id = f"{country_code}-00"
                    temp_conn.execute('''INSERT OR REPLACE INTO temp_regions 
                        (id, name, native, type, country_code, longitude, latitude) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                        (state_id, country_name, country_native, '', country_code, longitude, latitude))
                    region_count += 1

                # Commit periodically to avoid memory buildup
                if country_count % 100 == 0:
                    temp_conn.commit()
                    self.stdout.write(f'  Parsed {country_count} countries, {region_count} regions, {city_count} cities...')

        temp_conn.commit()
        self.stdout.write(f'✓ Parsing complete: {country_count} countries, {region_count} regions, {city_count} cities')

    def _process_countries_from_temp(self, temp_conn, batch_size):
        """Process countries from temporary database"""
        cursor = temp_conn.execute('SELECT country_code, name, native, subregion, capital, longitude, latitude FROM temp_countries')
        
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
                .only('country_code', 'name', 'native_name', 'subregion', 'capital', 'coordinates')
            }
            
            for row in rows:
                country_code, name, native, subregion, capital, longitude, latitude = row
                
                if country_code in existing_countries:
                    # Update existing
                    country_obj = existing_countries[country_code]
                    country_obj.name = name
                    country_obj.native_name = native
                    country_obj.subregion = subregion
                    country_obj.capital = capital
                    country_obj.coordinates = coordinates_from_lon_lat(longitude, latitude)
                    countries_to_update.append(country_obj)
                else:
                    countries_to_create.append(Country(
                        country_code=country_code,
                        name=name,
                        native_name=native,
                        subregion=subregion,
                        capital=capital,
                        coordinates=coordinates_from_lon_lat(longitude, latitude),
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
                        ['name', 'native_name', 'subregion', 'capital', 'coordinates'],
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
                    ['name', 'native_name', 'subregion', 'capital', 'coordinates'],
                    batch_size=batch_size
                )
        
        self.stdout.write(f'✓ Countries complete: {processed} processed')

    def _process_regions_from_temp(self, temp_conn, batch_size):
        """Process regions from temporary database"""
        # Get country mapping once
        country_map = {c.country_code: c for c in Country.objects.only('id', 'country_code', 'coordinates')}
        
        cursor = temp_conn.execute('SELECT id, name, native, country_code, longitude, latitude FROM temp_regions')
        
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
                .only('id', 'name', 'native_name', 'country', 'coordinates')
            }
            
            for row in rows:
                region_id, name, native, country_code, longitude, latitude = row
                country_obj = country_map.get(country_code)
                
                if not country_obj:
                    continue

                if longitude is None or latitude is None:
                    longitude = country_obj.longitude
                    latitude = country_obj.latitude
                    
                if region_id in existing_regions:
                    # Update existing
                    region_obj = existing_regions[region_id]
                    region_obj.name = name
                    region_obj.native_name = native
                    region_obj.country = country_obj
                    region_obj.coordinates = coordinates_from_lon_lat(longitude, latitude)
                    regions_to_update.append(region_obj)
                else:
                    regions_to_create.append(Region(
                        id=region_id,
                        name=name,
                        native_name=native,
                        country=country_obj,
                        coordinates=coordinates_from_lon_lat(longitude, latitude),
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
                        ['name', 'native_name', 'country', 'coordinates'],
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
                    ['name', 'native_name', 'country', 'coordinates'],
                    batch_size=batch_size
                )
        
        self.stdout.write(f'✓ Regions complete: {processed} processed')

    def _territory_links(self, temp_conn):
        """``{region_id: country_code}`` for the regions that the dataset also lists as a country."""
        countries = [
            {'code': code, 'name': name, 'native': native, 'lat': lat, 'lon': lon}
            for code, name, native, lon, lat in temp_conn.execute(
                'SELECT country_code, name, native, longitude, latitude FROM temp_countries'
            )
        ]
        regions = [
            {'id': region_id, 'country': code, 'name': name, 'native': native, 'type': region_type, 'lat': lat, 'lon': lon}
            for region_id, name, native, region_type, code, lon, lat in temp_conn.execute(
                'SELECT id, name, native, type, country_code, longitude, latitude FROM temp_regions'
            )
        ]
        return find_territory_links(countries, regions)

    def _link_territories(self, temp_conn):
        """Tie each region that the dataset also lists as a country to that country."""
        links = self._territory_links(temp_conn)

        country_ids = dict(Country.objects.values_list('country_code', 'id'))
        region_ids_by_country = {}
        for region_id, code in links.items():
            region_ids_by_country.setdefault(code, []).append(region_id)

        with transaction.atomic():
            # A link the data no longer supports is removed.
            Region.objects.filter(territory__isnull=False).exclude(id__in=list(links)).update(territory=None)
            for code, region_ids in region_ids_by_country.items():
                Region.objects.filter(id__in=region_ids).exclude(territory_id=country_ids[code]).update(
                    territory_id=country_ids[code]
                )

        self.stdout.write(f'✓ Territory links complete: {len(links)} regions linked')

    @staticmethod
    def _nearest_region(regions, lon, lat):
        """The id of the closest of ``(id, lon, lat)`` regions to a point, if one is near enough."""
        if lon is None or lat is None:
            return None
        best = None
        for region_id, region_lon, region_lat in regions:
            if region_lon is None or region_lat is None:
                continue
            km = distance_km(lat, lon, region_lat, region_lon)
            if km <= NEAREST_REGION_KM and (best is None or km < best[0]):
                best = (km, region_id)
        return best[1] if best else None

    def _merge_territory_cities(self, temp_conn):
        """
        Keep the cities of a region that is also a country on that country only.

        The dataset lists Puerto Rico's cities twice: 78 under the country and 255 under the US
        region. A city with the same name on both sides is the same town, so the copy under the
        larger country is dropped and recorded as an alias for the one under the territory. The
        others move to the nearest region of the territory. The region under the larger country
        is left with no cities of its own, so there is one place to find them and mark them.
        """
        links = self._territory_links(temp_conn)
        regions_of = {}
        for region_id, code, lon, lat in temp_conn.execute(
            'SELECT id, country_code, longitude, latitude FROM temp_regions'
        ):
            regions_of.setdefault(code, []).append((region_id, lon, lat))

        merged = moved = 0
        for parent_id, code in links.items():
            territory_regions = regions_of.get(code, [])
            parent_cities = temp_conn.execute(
                'SELECT id, name, longitude, latitude FROM temp_cities WHERE region_id = ?', (parent_id,)
            ).fetchall()
            if not parent_cities or not territory_regions:
                continue

            marks = ','.join('?' * len(territory_regions))
            territory_cities = temp_conn.execute(
                f'SELECT id, name FROM temp_cities WHERE region_id IN ({marks})', [region[0] for region in territory_regions]
            ).fetchall()
            duplicates = dict(pair_cities([(row[0], row[1]) for row in parent_cities], territory_cities))

            for city_id, _name, lon, lat in parent_cities:
                if city_id in duplicates:
                    temp_conn.execute(
                        'INSERT OR REPLACE INTO temp_city_aliases (old_id, new_id) VALUES (?, ?)',
                        (city_id, duplicates[city_id]),
                    )
                    temp_conn.execute('DELETE FROM temp_cities WHERE id = ?', (city_id,))
                    merged += 1
                    continue
                region_id = self._nearest_region(territory_regions, lon, lat)
                if region_id:
                    temp_conn.execute('UPDATE temp_cities SET region_id = ? WHERE id = ?', (region_id, city_id))
                    moved += 1

        temp_conn.commit()
        self.stdout.write(f'✓ Territory cities merged: {merged} duplicates dropped, {moved} moved')

    def _remap_merged_cities(self, temp_conn):
        """
        Point visits and places at the city a dropped duplicate was merged into, before it is deleted,
        and remember the dropped id so a backup that still uses it finds the city.
        """
        aliases = dict(temp_conn.execute('SELECT old_id, new_id FROM temp_city_aliases'))
        present = set(City.objects.filter(id__in=set(aliases.values())).values_list('id', flat=True))
        other_relations = [
            relation for relation in City._meta.related_objects
            if relation.one_to_many and relation.related_model is not VisitedCity
        ]

        with transaction.atomic():
            for old_id, new_id in aliases.items():
                if new_id not in present:
                    continue
                # A user who visited both keeps one visit.
                already = VisitedCity.objects.filter(city_id=new_id).values('user_id')
                VisitedCity.objects.filter(city_id=old_id, user_id__in=already).delete()
                VisitedCity.objects.filter(city_id=old_id).update(city_id=new_id)
                for relation in other_relations:
                    attname = relation.field.attname
                    relation.related_model.objects.filter(**{attname: old_id}).update(**{attname: new_id})
                CityAlias.objects.update_or_create(old_id=old_id, defaults={'city_id': new_id})

            # An alias the data no longer has is dropped, like any other record it stopped listing.
            CityAlias.objects.exclude(old_id__in=list(aliases)).delete()

        self.stdout.write(f'✓ {len(aliases)} merged cities remapped')

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
                    city_obj = City(
                        id=city_id,
                        name=name,
                        region=region_obj,
                        coordinates=coordinates_from_lon_lat(longitude, latitude),
                    )
                    cities_to_update.append(city_obj)
                else:
                    cities_to_create.append(City(
                        id=city_id,
                        name=name,
                        region=region_obj,
                        coordinates=coordinates_from_lon_lat(longitude, latitude),
                    ))
                
                processed += 1
                
            # Flush create batch (this is already fast)
            if cities_to_create:
                with transaction.atomic():
                    City.objects.bulk_create(cities_to_create, batch_size=batch_size, ignore_conflicts=True)
                cities_to_create.clear()
                
            if cities_to_update:
                with transaction.atomic():
                    City.objects.bulk_update(
                        cities_to_update,
                        ['name', 'region', 'coordinates'],
                        batch_size=batch_size,
                    )
                cities_to_update.clear()
                
            if processed % 5000 == 0:
                self.stdout.write(f'  Processed {processed} cities...')
                gc.collect()
        
        # Final flush
        if cities_to_create:
            with transaction.atomic():
                City.objects.bulk_create(cities_to_create, batch_size=batch_size, ignore_conflicts=True)
        if cities_to_update:
            with transaction.atomic():
                City.objects.bulk_update(
                    cities_to_update,
                    ['name', 'region', 'coordinates'],
                    batch_size=batch_size,
                )
        
        self.stdout.write(f'✓ Cities complete: {processed} processed')

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