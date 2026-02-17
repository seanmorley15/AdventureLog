"""
Django management command to synchronize visited regions/cities from Visit records.

This command processes all visits and marks their corresponding cities/regions as visited
using reverse geocoding of the parent item's coordinates.

Usage:
    python manage.py sync_visits_to_worldtravel
    python manage.py sync_visits_to_worldtravel --dry-run
    python manage.py sync_visits_to_worldtravel --user-id 123
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from adventures.models import Visit
from adventures.signals import mark_city_region_visited, _get_visit_coordinates
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = 'Sync visited regions/cities from Visit records using reverse geocoding'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without making changes',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='Sync only for a specific user ID',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output for each visit',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        user_id = options.get('user_id')
        verbose = options['verbose']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        # Build visits queryset
        visits_queryset = Visit.objects.select_related(
            'user', 'location', 'transportation', 'lodging'
        ).filter(user__isnull=False)

        if user_id:
            visits_queryset = visits_queryset.filter(user_id=user_id)

        try:
            total_visits = visits_queryset.count()
        except Exception as e:
            # May fail during migration if schema is changing
            self.stdout.write(self.style.WARNING(f'Could not count visits (migration in progress?): {e}'))
            return

        if total_visits == 0:
            self.stdout.write(self.style.WARNING('No visits found'))
            return

        self.stdout.write(f'Processing {total_visits} visit(s)...\n')

        # Track statistics
        total_cities_marked = 0
        total_regions_marked = 0
        visits_processed = 0
        visits_with_coords = 0
        visits_with_changes = 0

        try:
            visits_list = list(visits_queryset)
        except Exception as e:
            # May fail during migration if schema is changing
            self.stdout.write(self.style.WARNING(f'Could not load visits (migration in progress?): {e}'))
            return

        for visit in visits_list:
            visits_processed += 1

            lat, lon = _get_visit_coordinates(visit)

            if lat is None or lon is None:
                if verbose:
                    self.stdout.write(f'  Visit {visit.id}: No coordinates')
                continue

            visits_with_coords += 1

            if dry_run:
                if verbose:
                    self.stdout.write(
                        f'  Visit {visit.id}: Would geocode ({lat}, {lon}) for user {visit.user.username}'
                    )
                continue

            try:
                city_marked, region_marked = mark_city_region_visited(
                    visit.user, lat, lon
                )

                if city_marked:
                    total_cities_marked += 1
                if region_marked:
                    total_regions_marked += 1
                if city_marked or region_marked:
                    visits_with_changes += 1

                if verbose and (city_marked or region_marked):
                    self.stdout.write(
                        f'  Visit {visit.id}: city={city_marked}, region={region_marked}'
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing visit {visit.id}: {str(e)}')
                )
                logger.exception(f'Error processing visit {visit.id}')

            # Progress indicator
            if visits_processed % 100 == 0:
                self.stdout.write(f'Processed {visits_processed}/{total_visits} visits...')

        # Summary
        self.stdout.write('\n' + '=' * 60)
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'DRY RUN COMPLETE:\n'
                    f'  Visits processed: {visits_processed}\n'
                    f'  Visits with coordinates: {visits_with_coords}\n'
                    f'  Would geocode {visits_with_coords} visits'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'SYNC COMPLETE:\n'
                    f'  Visits processed: {visits_processed}\n'
                    f'  Visits with coordinates: {visits_with_coords}\n'
                    f'  Visits with changes: {visits_with_changes}\n'
                    f'  New regions marked: {total_regions_marked}\n'
                    f'  New cities marked: {total_cities_marked}'
                )
            )
