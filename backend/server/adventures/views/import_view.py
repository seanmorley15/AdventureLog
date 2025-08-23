# import_view.py
import datetime
import json
import os
import tempfile
import zipfile
from zoneinfo import ZoneInfo

from adventures.models import Location, Collection, Category, Visit, ContentImage
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

User = get_user_model()


class ImportViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(
        detail=False,
        methods=['post'],
        parser_classes=[MultiPartParser],
        url_path='polarsteps',
        url_name='polarsteps'
    )
    def import_polarsteps(self, request):
        """
        Import data from polarsteps ZIP file
        """
        if 'file' not in request.FILES:
            return Response({'message': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        import_file = request.FILES['file']
        user = request.user

        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            for chunk in import_file.chunks():
                tmp_file.write(chunk)
            tmp_file_path = tmp_file.name

        try:
            summary = {
                'categories': 0, 'collections': 0, 'locations': 0,
                'transportation': 0, 'notes': 0, 'checklists': 0,
                'checklist_items': 0, 'lodging': 0, 'images': 0,
                'attachments': 0, 'visited_cities': 0, 'visited_regions': 0,
                'trails': 0, 'activities': 0, 'gpx_files': 0
            }

            with zipfile.ZipFile(tmp_file_path, 'r') as zip_file:
                trip_files = [name for name in zip_file.namelist() if name.endswith('trip.json')]

                if not trip_files:
                    return Response({'message': 'Invalid backup file - missing trip.json files'},
                                    status=status.HTTP_400_BAD_REQUEST)

                for trip_file in trip_files:
                    import_data = json.loads(zip_file.read(trip_file).decode('utf-8'))

                    with transaction.atomic():
                        summary = self._import_polarsteps(import_data, zip_file, user, summary)

                return Response({
                    'success': True,
                    'message': 'Polarsteps data imported successfully',
                    'summary': summary
                }, status=status.HTTP_200_OK)

        except json.JSONDecodeError:
            return Response({'message': 'Invalid JSON in backup file'},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            import logging
            logging.error("Import failed", exc_info=True)
            return Response({'message': 'An internal error occurred during import'},
                            status=status.HTTP_400_BAD_REQUEST)
        finally:
            os.unlink(tmp_file_path)

    def _import_polarsteps(self, import_data, zip_file, user, summary):
        """Import polarsteps data and return summary"""
        # Create Category
        category, _ = Category.objects.get_or_create(
            user=user,
            name='import',
            defaults={'display_name': 'General', 'icon': '🌍'}
        )

        # Create Collection
        collection = Collection.objects.create(
            user=user,
            name=import_data.get('name'),
            description=import_data.get('summary'),
            created_at=timestamp_to_datetime(import_data.get('creation_time'), import_data.get('timezone_id')),
            start_date=timestamp_to_date(import_data.get('start_date'), import_data.get('timezone_id')),
            end_date=timestamp_to_date(import_data.get('end_date'), import_data.get('timezone_id'))
        )
        summary['collections'] += 1

        # Import each step as a Location + Visit
        for adv_data in import_data.get('all_steps', []):
            if adv_data.get('is_deleted') is True:
                continue

            location = Location(
                user=user,
                name=adv_data.get('display_name') or adv_data.get('name') or adv_data['location']['name'],
                description=adv_data.get('description'),
                longitude=adv_data['location']['lon'],
                latitude=adv_data['location']['lat'],
                category=category,
                created_at=timestamp_to_datetime(adv_data.get('creation_time'), adv_data.get('timezone_id'))
            )
            location.save(_skip_geocode=True)
            location.collections.add(collection)

            # Compute start and end times
            start_dt = timestamp_to_datetime(adv_data.get('start_time'), adv_data.get('timezone_id'))
            end_dt = timestamp_to_datetime(adv_data.get('end_time'), adv_data.get('timezone_id'))

            # Fallback: if end_time missing, use start_time
            if end_dt is None and start_dt is not None:
                end_dt = start_dt

            Visit.objects.create(
                location=location,
                start_date=start_dt,
                end_date=end_dt,
                timezone=adv_data.get('timezone_id'),
                created_at=timestamp_to_datetime(adv_data.get('creation_time'), adv_data.get('timezone_id'))
            )

            # Import images
            step_id = adv_data.get('id')
            if step_id is not None:
                folder_name = None
                # Find folder ending with _{step_id}
                for name in zip_file.namelist():
                    parts = name.split('/')
                    for part in parts:
                        if part.endswith(f'_{step_id}'):
                            folder_name = '/'.join(parts[:parts.index(part) + 1]) + '/photos/'
                            print(f"Looking for images in folder: {folder_name}", flush=True)
                            break
                    if folder_name:
                        break

                if folder_name:
                    content_type = ContentType.objects.get(model='location')

                    for zip_name in zip_file.namelist():
                        if zip_name.startswith(folder_name) and zip_name.count('/') == folder_name.count('/'):
                            print(f"Importing image: {zip_name}", flush=True)
                            try:
                                img_content = zip_file.read(zip_name)
                                filename = os.path.basename(zip_name)
                                img_file = ContentFile(img_content, name=filename)

                                ContentImage.objects.create(
                                    user=user,
                                    image=img_file,
                                    is_primary=False,
                                    content_type=content_type,
                                    object_id=location.id
                                )
                                summary['images'] += 1
                            except KeyError:
                                continue

            summary['locations'] += 1

        return summary


def timestamp_to_datetime(ts, tz_name=None):
    """Convert a Unix timestamp (seconds) to a timezone-aware datetime."""
    if ts is None:
        return None
    try:
        dt_utc = datetime.datetime.fromtimestamp(ts, tz=ZoneInfo("UTC"))
        if tz_name:
            tz = ZoneInfo(tz_name)
            return dt_utc.astimezone(tz)
        return dt_utc
    except (TypeError, ValueError, Exception):
        return None


def timestamp_to_date(ts, tz_name=None):
    """Convert a Unix timestamp (seconds) to a date in the given timezone, or None if invalid."""
    if ts is None:
        return None
    try:
        # Convert timestamp to UTC datetime
        dt_utc = datetime.datetime.fromtimestamp(ts, tz=ZoneInfo("UTC"))
        if tz_name:
            tz = ZoneInfo(tz_name)
            dt_local = dt_utc.astimezone(tz)
        else:
            dt_local = dt_utc
        return dt_local.date()
    except (TypeError, ValueError, OSError):
        return None
