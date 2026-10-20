"""
Django management command to synchronize visited regions and cities based on user locations.

This command processes all users' visited locations and marks their regions and cities as visited.
It's designed to be run periodically (e.g., nightly cron job) to keep visited regions/cities up to date.

Usage:
    python manage.py sync_visited_regions
    python manage.py sync_visited_regions --dry-run
    python manage.py sync_visited_regions --user-id 123
    python manage.py sync_visited_regions --batch-size 50
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from adventures.models import Location
from worldtravel.services import mark_cities_visited, mark_regions_visited
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = 'Synchronize visited regions and cities based on user locations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without making changes',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='Sync visited regions for a specific user ID only',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of users to process in each batch (default: 100)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output for each user',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        user_id = options.get('user_id')
        batch_size = options['batch_size']
        verbose = options['verbose']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        # Build user queryset
        users_queryset = User.objects.all()
        
        if user_id:
            users_queryset = users_queryset.filter(id=user_id)
            if not users_queryset.exists():
                raise CommandError(f'User with ID {user_id} not found')

        total_users = users_queryset.count()
        
        if total_users == 0:
            self.stdout.write(self.style.WARNING('No users found'))
            return

        self.stdout.write(f'Processing {total_users} user(s)...\n')

        # Track overall statistics
        total_new_regions = 0
        total_new_cities = 0
        users_processed = 0
        users_with_changes = 0

        # Process users in batches to manage memory
        user_ids = list(users_queryset.values_list('id', flat=True))
        
        for i in range(0, len(user_ids), batch_size):
            batch_user_ids = user_ids[i:i + batch_size]
            
            for user_id in batch_user_ids:
                try:
                    new_regions, new_cities = self._process_user(
                        user_id, dry_run, verbose
                    )
                    
                    total_new_regions += new_regions
                    total_new_cities += new_cities
                    users_processed += 1
                    
                    if new_regions > 0 or new_cities > 0:
                        users_with_changes += 1
                    
                    # Progress indicator for large batches
                    if users_processed % 50 == 0:
                        self.stdout.write(
                            f'Processed {users_processed}/{total_users} users...'
                        )
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Error processing user {user_id}: {str(e)}'
                        )
                    )
                    logger.exception(f'Error processing user {user_id}')

        # Summary
        self.stdout.write('\n' + '='*60)
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'DRY RUN COMPLETE:\n'
                    f'  Users processed: {users_processed}\n'
                    f'  Users with changes: {users_with_changes}\n'
                    f'  Would create {total_new_regions} new visited regions\n'
                    f'  Would create {total_new_cities} new visited cities'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'SYNC COMPLETE:\n'
                    f'  Users processed: {users_processed}\n'
                    f'  Users with changes: {users_with_changes}\n'
                    f'  Created {total_new_regions} new visited regions\n'
                    f'  Created {total_new_cities} new visited cities'
                )
            )

    def _process_user(self, user_id, dry_run=False, verbose=False):
        """
        Process a single user and return counts of new regions and cities.
        Returns: (new_regions_count, new_cities_count)
        """
        # Get all visited locations with their region and city data in a single query
        visited_locations = Location.objects.filter(
            user_id=user_id
        ).select_related('region', 'city')
        
        # Collect unique regions and cities from visited locations
        regions_to_mark = set()
        cities_to_mark = set()
        
        for location in visited_locations:
            # Only process locations that are marked as visited
            if not location.is_visited_status():
                continue
            
            if location.region_id:
                regions_to_mark.add(location.region_id)
            
            if location.city_id:
                cities_to_mark.add(location.city_id)
        
        # Early exit if no regions or cities to mark
        if not regions_to_mark and not cities_to_mark:
            return 0, 0
        
        new_regions_count = 0
        new_cities_count = 0
        
        # Process regions
        if regions_to_mark:
            new_regions_count = self._sync_visited_regions(
                user_id, regions_to_mark, dry_run
            )
        
        # Process cities
        if cities_to_mark:
            new_cities_count = self._sync_visited_cities(
                user_id, cities_to_mark, dry_run
            )
        
        if verbose and (new_regions_count > 0 or new_cities_count > 0):
            self.stdout.write(
                f'User {user_id}: '
                f'{new_regions_count} new regions, '
                f'{new_cities_count} new cities'
            )
        
        return new_regions_count, new_cities_count

    def _sync_visited_regions(self, user_id, region_ids, dry_run=False):
        """Sync visited regions for a user. Returns count of new regions created."""
        return len(mark_regions_visited(user_id, region_ids, dry_run=dry_run))

    def _sync_visited_cities(self, user_id, city_ids, dry_run=False):
        """Sync visited cities for a user. Returns count of new cities created."""
        return len(mark_cities_visited(user_id, city_ids, dry_run=dry_run))
