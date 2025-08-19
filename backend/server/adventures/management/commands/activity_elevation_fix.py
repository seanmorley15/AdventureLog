"""
Django management command to recalculate elevation data for all activities with GPX files.

Usage:
    python manage.py recalculate_elevation
    python manage.py recalculate_elevation --dry-run
    python manage.py recalculate_elevation --activity-id 123
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from adventures.models import Activity
import gpxpy
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Recalculate elevation data for activities with GPX files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--activity-id',
            type=int,
            help='Recalculate elevation for a specific activity ID only',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of activities to process in each batch (default: 100)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        activity_id = options.get('activity_id')
        batch_size = options['batch_size']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        # Build queryset
        queryset = Activity.objects.filter(gpx_file__isnull=False).exclude(gpx_file='')
        
        if activity_id:
            queryset = queryset.filter(id=activity_id)
            if not queryset.exists():
                raise CommandError(f'Activity with ID {activity_id} not found or has no GPX file')

        total_count = queryset.count()
        
        if total_count == 0:
            self.stdout.write(
                self.style.WARNING('No activities found with GPX files')
            )
            return

        self.stdout.write(f'Found {total_count} activities with GPX files to process')

        updated_count = 0
        error_count = 0
        
        # Process in batches to avoid memory issues with large datasets
        for i in range(0, total_count, batch_size):
            batch = queryset[i:i + batch_size]
            
            for activity in batch:
                try:
                    if self._process_activity(activity, dry_run):
                        updated_count += 1
                    
                    # Progress indicator
                    if (updated_count + error_count) % 50 == 0:
                        self.stdout.write(
                            f'Processed {updated_count + error_count}/{total_count} activities...'
                        )
                        
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'Error processing activity {activity.id}: {str(e)}'
                        )
                    )

        # Summary
        self.stdout.write('\n' + '='*50)
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'DRY RUN COMPLETE: Would update {updated_count} activities'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully updated {updated_count} activities'
                )
            )
        
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(f'Encountered errors with {error_count} activities')
            )

    def _process_activity(self, activity, dry_run=False):
        """Process a single activity and return True if it was updated."""
        try:
            # Get elevation data from GPX file
            elevation_gain, elevation_loss, elevation_high, elevation_low = \
                self._get_elevation_data_from_gpx(activity.gpx_file)

            # Check if values would actually change
            current_values = (
                getattr(activity, 'elevation_gain', None) or 0,
                getattr(activity, 'elevation_loss', None) or 0,
                getattr(activity, 'elev_high', None) or 0,
                getattr(activity, 'elev_low', None) or 0,
            )
            
            new_values = (elevation_gain, elevation_loss, elevation_high, elevation_low)
            
            # Only update if values are different (with small tolerance for floating point)
            if self._values_significantly_different(current_values, new_values):
                
                if dry_run:
                    self.stdout.write(
                        f'Activity {activity.id}: '
                        f'gain: {current_values[0]:.1f} → {new_values[0]:.1f}, '
                        f'loss: {current_values[1]:.1f} → {new_values[1]:.1f}, '
                        f'high: {current_values[2]:.1f} → {new_values[2]:.1f}, '
                        f'low: {current_values[3]:.1f} → {new_values[3]:.1f}'
                    )
                    return True
                else:
                    # Update the activity
                    with transaction.atomic():
                        activity.elevation_gain = elevation_gain
                        activity.elevation_loss = elevation_loss
                        activity.elev_high = elevation_high
                        activity.elev_low = elevation_low
                        activity.save(update_fields=[
                            'elevation_gain', 'elevation_loss', 'elev_high', 'elev_low'
                        ])
                    
                    self.stdout.write(
                        f'Updated activity {activity.id}: '
                        f'gain: {elevation_gain:.1f}m, loss: {elevation_loss:.1f}m, '
                        f'high: {elevation_high:.1f}m, low: {elevation_low:.1f}m'
                    )
                    return True
            else:
                # Values are the same, skip
                return False
                
        except Exception as e:
            logger.error(f'Error processing activity {activity.id}: {str(e)}')
            raise

    def _values_significantly_different(self, current, new, tolerance=0.1):
        """Check if elevation values are significantly different."""
        for c, n in zip(current, new):
            if abs(c - n) > tolerance:
                return True
        return False

    def _get_elevation_data_from_gpx(self, gpx_file) -> Tuple[float, float, float, float]:
        """
        Extract elevation data from a GPX file.
        Returns: (elevation_gain, elevation_loss, elevation_high, elevation_low)
        """
        try:
            # Parse the GPX file
            gpx_file.seek(0)  # Reset file pointer if needed
            gpx = gpxpy.parse(gpx_file)
            
            elevations = []
            
            # Extract all elevation points from tracks and track segments
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        if point.elevation is not None:
                            elevations.append(point.elevation)
            
            # Also check waypoints for elevation data
            for waypoint in gpx.waypoints:
                if waypoint.elevation is not None:
                    elevations.append(waypoint.elevation)
            
            # If no elevation data found, return zeros
            if not elevations:
                return 0.0, 0.0, 0.0, 0.0
            
            # Calculate basic stats
            elevation_high = max(elevations)
            elevation_low = min(elevations)
            
            # Calculate gain and loss by comparing consecutive points
            elevation_gain = 0.0
            elevation_loss = 0.0
            
            # Apply simple smoothing to reduce GPS noise (optional)
            smoothed_elevations = self._smooth_elevations(elevations)
            
            for i in range(1, len(smoothed_elevations)):
                diff = smoothed_elevations[i] - smoothed_elevations[i-1]
                if diff > 0:
                    elevation_gain += diff
                else:
                    elevation_loss += abs(diff)
            
            return elevation_gain, elevation_loss, elevation_high, elevation_low
            
        except Exception as e:
            logger.error(f"Error parsing GPX file: {e}")
            raise

    def _smooth_elevations(self, elevations, window_size=3):
        """
        Apply simple moving average smoothing to reduce GPS elevation noise.
        """
        if len(elevations) < window_size:
            return elevations
        
        smoothed = []
        half_window = window_size // 2
        
        for i in range(len(elevations)):
            start = max(0, i - half_window)
            end = min(len(elevations), i + half_window + 1)
            smoothed.append(sum(elevations[start:end]) / (end - start))
        
        return smoothed