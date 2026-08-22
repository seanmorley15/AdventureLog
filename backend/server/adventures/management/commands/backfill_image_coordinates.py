"""
Backfill GPS coordinates on existing ContentImage records from stored files or Immich.

Uploaded images are stored as WEBP, which may no longer contain EXIF GPS data. This command
attempts extraction from the stored file first, then falls back to Immich asset metadata when
an immich_id is present.

Usage:
    python manage.py backfill_image_coordinates
    python manage.py backfill_image_coordinates --dry-run
    python manage.py backfill_image_coordinates --user-id 123
    python manage.py backfill_image_coordinates --batch-size 50
    python manage.py backfill_image_coordinates --force
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.files.storage import default_storage

from adventures.models import ContentImage
from adventures.services.images.metadata import resolve_coordinates_for_image
from adventures.utils.geo import point_to_lat_lon
from integrations.models import ImmichIntegration

User = get_user_model()


class Command(BaseCommand):
    help = 'Extract and store GPS coordinates for existing ContentImage records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would change without writing to the database',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='Process images for a specific user ID only',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of images to process per progress log batch (default: 100)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-extract coordinates even when coordinates are already set',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Log each updated or skipped image',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        user_id = options.get('user_id')
        batch_size = max(1, options['batch_size'])
        force = options['force']
        verbose = options['verbose']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        queryset = ContentImage.objects.all().select_related('user', 'content_type')
        if not force:
            queryset = queryset.filter(coordinates__isnull=True)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
            if not queryset.exists() and not ContentImage.objects.filter(user_id=user_id).exists():
                raise CommandError(f'User with ID {user_id} not found')

        total = queryset.count()
        if total == 0:
            self.stdout.write(self.style.WARNING('No images matched the selected criteria'))
            return

        self.stdout.write(f'Processing {total} image(s)...')

        immich_by_user = {
            integration.user_id: integration
            for integration in ImmichIntegration.objects.all()
        }

        stats = {
            'processed': 0,
            'updated': 0,
            'skipped_existing': 0,
            'no_gps_found': 0,
            'file_missing': 0,
            'errors': 0,
        }

        for image in queryset.iterator(chunk_size=batch_size):
            stats['processed'] += 1

            if image.coordinates and not force:
                stats['skipped_existing'] += 1
                continue

            if not image.image and not image.immich_id:
                stats['no_gps_found'] += 1
                if verbose:
                    self.stdout.write(f'  skip {image.id}: no file or Immich reference')
                continue

            if image.image and not image.immich_id:
                try:
                    if not default_storage.exists(image.image.name):
                        stats['file_missing'] += 1
                        if verbose:
                            self.stdout.write(f'  skip {image.id}: stored file missing')
                        continue
                except Exception:
                    stats['errors'] += 1
                    if verbose:
                        self.stdout.write(f'  error {image.id}: could not verify stored file')
                    continue

            try:
                point = resolve_coordinates_for_image(
                    image,
                    immich_integration=immich_by_user.get(image.user_id),
                )
            except Exception as exc:
                stats['errors'] += 1
                if verbose:
                    self.stdout.write(f'  error {image.id}: {exc}')
                continue

            if not point:
                stats['no_gps_found'] += 1
                if verbose:
                    self.stdout.write(f'  skip {image.id}: no GPS metadata found')
                continue

            lat, lon = point_to_lat_lon(point)
            if dry_run:
                stats['updated'] += 1
                if verbose:
                    self.stdout.write(
                        f'  would update {image.id}: lat={lat}, lon={lon}'
                    )
                continue

            image.coordinates = point
            image.save(update_fields=['coordinates'])
            stats['updated'] += 1
            if verbose:
                self.stdout.write(f'  updated {image.id}: lat={lat}, lon={lon}')

            if stats['processed'] % batch_size == 0:
                self.stdout.write(f'  ... processed {stats["processed"]}/{total}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Backfill complete'))
        self.stdout.write(f'  Processed: {stats["processed"]}')
        self.stdout.write(f'  Updated: {stats["updated"]}')
        self.stdout.write(f'  Skipped (already had coordinates): {stats["skipped_existing"]}')
        self.stdout.write(f'  No GPS found: {stats["no_gps_found"]}')
        self.stdout.write(f'  Missing files: {stats["file_missing"]}')
        self.stdout.write(f'  Errors: {stats["errors"]}')
