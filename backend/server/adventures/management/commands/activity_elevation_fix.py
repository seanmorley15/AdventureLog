"""
Recompute the elevation of activities from their stored GPX tracks.

Usage:
    python manage.py activity_elevation_fix --dry-run
    python manage.py activity_elevation_fix
    python manage.py activity_elevation_fix --activity-id <uuid>
    python manage.py activity_elevation_fix --force

Elevation is measured from the track with the same method new uploads use. A total a device or
provider reported (a FIT upload, a Strava or Endurain import) is replaced by that measurement, so
imported activities are skipped unless ``--force`` is given. A track without altitude is never
touched.
"""

import logging

from django.core.management.base import BaseCommand, CommandError

from adventures.models import Activity
from adventures.services.activities import metrics, read_track
from core.errors import ServiceError

logger = logging.getLogger(__name__)

FIELDS = ('elevation_gain', 'elevation_loss', 'elev_high', 'elev_low')
# Changes smaller than this many meters are noise, not corrections.
TOLERANCE = 0.1


class Command(BaseCommand):
    help = 'Recompute elevation gain, loss, high and low from the stored GPX tracks'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would change without saving')
        parser.add_argument('--activity-id', type=str, help='Only this activity (a UUID)')
        parser.add_argument(
            '--force', action='store_true',
            help='Also replace the totals of activities imported from Strava or Endurain',
        )

    def handle(self, *args, **options):
        dry_run, force = options['dry_run'], options['force']
        queryset = Activity.objects.exclude(gpx_file='').exclude(gpx_file__isnull=True)
        if options['activity_id']:
            queryset = queryset.filter(pk=options['activity_id'])
            if not queryset.exists():
                raise CommandError(f'No activity {options["activity_id"]} with a GPX file')
        if not force:
            queryset = queryset.filter(external_service_id__isnull=True) | queryset.filter(external_service_id='')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN: nothing will be saved'))

        updated = failed = 0
        for activity in queryset.iterator():
            try:
                if self._recompute(activity, dry_run):
                    updated += 1
            except (ServiceError, OSError, ValueError) as error:
                failed += 1
                self.stdout.write(self.style.ERROR(f'Activity {activity.id}: {error}'))

        verb = 'Would update' if dry_run else 'Updated'
        self.stdout.write(self.style.SUCCESS(f'{verb} {updated} activities'))
        if failed:
            self.stdout.write(self.style.WARNING(f'{failed} could not be read'))

    def _recompute(self, activity, dry_run):
        """Save the track's elevation on ``activity``; ``True`` when it differs from what was stored."""
        with activity.gpx_file.open('rb') as file:
            track = read_track(file)
        climb = metrics.elevation(track.segments)
        if climb is None:
            return False

        new = dict(zip(FIELDS, climb))
        changed = any(abs((getattr(activity, name) or 0) - value) > TOLERANCE for name, value in new.items())
        if not changed:
            return False

        self.stdout.write(
            f'Activity {activity.id}: gain {activity.elevation_gain or 0:.0f} -> {new["elevation_gain"]:.0f} m, '
            f'loss {activity.elevation_loss or 0:.0f} -> {new["elevation_loss"]:.0f} m'
        )
        if not dry_run:
            for name, value in new.items():
                setattr(activity, name, value)
            activity.save(update_fields=list(FIELDS))
        return True
