# views.py
import json
import zipfile
import tempfile
import os
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.http import HttpResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from users.services.account_deletion import clear_user_adventure_data
from adventures.models import (
    Location, Collection, Transportation, Note, Checklist, ChecklistItem,
    ContentImage, ContentAttachment, Category, Lodging, Visit, Trail, Activity,
    CollectionItineraryItem, CollectionItineraryDay, CollectionGuestLink, CollectionMember
)
from worldtravel.models import VisitedCity, VisitedRegion, City, Region, Country
from adventures.utils.geo import make_point, point_to_lat_lon
from adventures.utils.collection_type import (
    BACKUP_SCHEMA,
    UnsupportedBackupSchema,
    backup_has_day_plan,
    ensure_backup_schema_supported,
    imported_story_groups,
    imported_visibility,
    resolve_imported_collection_type,
)
from adventures.utils.itinerary_days import convert_collection
from adventures.utils.timezones import timezone_or_utc
from adventures.services.images.metadata import create_content_image

User = get_user_model()

class BackupViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    """
    Simple ViewSet for handling backup and import operations
    """

    def _normalize_money_amount(self, value):
        """Return a Decimal amount from legacy or canonical backup values."""
        if value is None:
            return None

        if isinstance(value, Decimal):
            return value

        if isinstance(value, (int, float)):
            try:
                return Decimal(str(value))
            except (InvalidOperation, ValueError):
                return None

        if not isinstance(value, str):
            return None

        text = value.strip()
        if not text:
            return None

        # Accept values like "$1,553.59" and "USD 1,553.59".
        cleaned = re.sub(r'[^0-9,\.\-]', '', text)
        if not cleaned:
            return None

        if ',' in cleaned and '.' in cleaned:
            if cleaned.rfind(',') > cleaned.rfind('.'):
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned:
            parts = cleaned.split(',')
            if len(parts) == 2 and len(parts[-1]) in (1, 2):
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')

        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None

    def _resolve_import_country(self, adv_data, region=None):
        """
        Resolve a location's Country during import without trusting raw Country PKs.

        Country.id is an auto-increment integer that differs between installs (it
        depends on the order the countries dataset was loaded), so a PK from a
        backup can silently point at a different country (e.g. Germany -> Ghana).
        Stable identifiers are used instead, in order of reliability:
          1. the resolved region's country (region IDs are ISO 3166-2 strings),
          2. the exported ISO 3166-1 alpha-2 `country_code`,
          3. legacy backups only: the raw Country PK, as a last resort.
        """
        if region is not None and region.country_id:
            return region.country

        country_code = adv_data.get('country_code')
        if isinstance(country_code, str) and country_code.strip():
            country = Country.objects.filter(country_code=country_code.strip().upper()).first()
            if country:
                return country

        # Legacy backups (no country_code): fall back to the city's/region's ISO
        # prefix before trusting the raw PK.
        for key in ('region', 'city'):
            ref = adv_data.get(key)
            if isinstance(ref, str) and '-' in ref:
                country = Country.objects.filter(country_code=ref.split('-', 1)[0].upper()).first()
                if country:
                    return country

        legacy_id = adv_data.get('country')
        if legacy_id:
            return Country.objects.filter(id=legacy_id).first()
        return None

    def _parse_money(self, value, currency=None, default_currency='USD'):
        """Parse a backup money value and return schema-safe (amount, currency)."""
        parsed_currency = currency
        parsed_value = value

        if isinstance(value, dict):
            parsed_value = value.get('amount')
            parsed_currency = parsed_currency or value.get('currency')

        amount = self._normalize_money_amount(parsed_value)
        if amount is None:
            # django-money stores currency in a separate non-null column even when
            # the monetary amount itself is empty, so imports must preserve a
            # default currency for blank legacy values.
            return None, default_currency

        normalized_currency = (parsed_currency or default_currency)
        if isinstance(normalized_currency, str):
            normalized_currency = normalized_currency.strip().upper() or default_currency
        else:
            normalized_currency = default_currency

        return amount, normalized_currency

    def _optional_str(self, value):
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _export_day_files(self, export_data, collection, collection_export_id):
        """Schema 4: trails, activities, and photos whose parent is a day or Ideas."""
        from adventures.utils.day_files import day_file_activities, day_file_images, day_file_trails

        trail_keys = {}
        for trail in day_file_trails(collection):
            export_id = len(export_data['day_trails'])
            trail_keys[trail.id] = export_id
            export_data['day_trails'].append({
                'export_id': export_id,
                'collection_export_id': collection_export_id,
                'day_index': trail.day.index if trail.day_id else None,
                'name': trail.name,
                'link': trail.link,
                'wanderer_id': trail.wanderer_id,
                'wanderer_author_username': trail.wanderer_author_username,
                'wanderer_author_domain': trail.wanderer_author_domain,
                'span_end_index': trail.span_end_index,
                'images': self._serialize_images(trail.images),
            })
        for activity in day_file_activities(collection):
            gpx_filename = None
            if activity.gpx_file:
                gpx_filename = activity.gpx_file.name.split('/')[-1]
            export_data['day_activities'].append({
                'collection_export_id': collection_export_id,
                'day_index': activity.day.index if activity.day_id else None,
                'name': activity.name,
                'sport_type': activity.sport_type,
                'distance': float(activity.distance) if activity.distance else None,
                'moving_time': activity.moving_time.total_seconds() if activity.moving_time else None,
                'elapsed_time': activity.elapsed_time.total_seconds() if activity.elapsed_time else None,
                'rest_time': activity.rest_time.total_seconds() if activity.rest_time else None,
                'elevation_gain': float(activity.elevation_gain) if activity.elevation_gain else None,
                'elevation_loss': float(activity.elevation_loss) if activity.elevation_loss else None,
                'elev_high': float(activity.elev_high) if activity.elev_high else None,
                'elev_low': float(activity.elev_low) if activity.elev_low else None,
                'start_date': activity.start_date.isoformat() if activity.start_date else None,
                'start_date_local': activity.start_date_local.isoformat() if activity.start_date_local else None,
                'timezone': activity.timezone,
                'average_speed': float(activity.average_speed) if activity.average_speed else None,
                'max_speed': float(activity.max_speed) if activity.max_speed else None,
                'average_cadence': float(activity.average_cadence) if activity.average_cadence else None,
                'calories': float(activity.calories) if activity.calories else None,
                'gpx_filename': gpx_filename,
                'trail_export_id': trail_keys.get(activity.trail_id),
                'images': self._serialize_images(activity.images),
            })
        day_ct = ContentType.objects.get_for_model(CollectionItineraryDay)
        collection_ct = ContentType.objects.get_for_model(Collection)
        for image in day_file_images(collection).select_related('content_type'):
            if image.content_type_id not in (day_ct.id, collection_ct.id):
                continue
            entry = self._serialize_images(ContentImage.objects.filter(pk=image.pk))
            if not entry:
                continue
            payload = entry[0]
            payload['collection_export_id'] = collection_export_id
            if image.content_type_id == day_ct.id:
                day = CollectionItineraryDay.objects.filter(pk=image.object_id).first()
                payload['day_index'] = day.index if day else None
            else:
                payload['day_index'] = None
            export_data['day_images'].append(payload)

    def _import_day_files(self, backup_data, zip_file, user, collection_map, day_map, summary):
        """Restore schema 4 rows. A backup without these keys imports nothing extra."""
        from datetime import timedelta
        from django.core.files.base import ContentFile
        from django.utils.dateparse import parse_datetime

        trail_map = {}
        content_type_trail = ContentType.objects.get_for_model(Trail)
        content_type_activity = ContentType.objects.get_for_model(Activity)
        content_type_day = ContentType.objects.get_for_model(CollectionItineraryDay)
        content_type_collection = ContentType.objects.get_for_model(Collection)
        for trail_data in backup_data.get('day_trails') or []:
            collection = collection_map.get(trail_data.get('collection_export_id'))
            if not collection:
                continue
            day_index = trail_data.get('day_index')
            day = day_map.get((trail_data.get('collection_export_id'), day_index)) if day_index else None
            if day_index and day is None:
                continue
            parsed = self._parse_trail_import(trail_data)
            if not parsed:
                summary['trails_skipped'] = summary.get('trails_skipped', 0) + 1
                continue
            trail = Trail.objects.create(
                user=user,
                location=None,
                day=day,
                collection=None if day else collection,
                name=parsed['name'],
                link=parsed['link'],
                wanderer_id=parsed['wanderer_id'],
                wanderer_author_username=parsed['wanderer_author_username'],
                wanderer_author_domain=parsed['wanderer_author_domain'],
                span_end_index=trail_data.get('span_end_index') if day else None,
            )
            trail_map[trail_data.get('export_id')] = trail
            self._import_images(
                trail_data.get('images') or [],
                zip_file,
                user,
                content_type_trail,
                trail.id,
                summary,
            )
            summary['trails'] = summary.get('trails', 0) + 1

        for activity_data in backup_data.get('day_activities') or []:
            collection = collection_map.get(activity_data.get('collection_export_id'))
            if not collection:
                continue
            day_index = activity_data.get('day_index')
            day = day_map.get((activity_data.get('collection_export_id'), day_index)) if day_index else None
            if day_index and day is None:
                continue

            def seconds(value):
                return timedelta(seconds=float(value)) if value not in (None, '') else None

            activity = Activity(
                user=user,
                visit=None,
                day=day,
                collection=None if day else collection,
                trail=trail_map.get(activity_data.get('trail_export_id')),
                name=activity_data.get('name') or 'Activity',
                sport_type=activity_data.get('sport_type') or 'General',
                distance=activity_data.get('distance'),
                moving_time=seconds(activity_data.get('moving_time')),
                elapsed_time=seconds(activity_data.get('elapsed_time')),
                rest_time=seconds(activity_data.get('rest_time')),
                elevation_gain=activity_data.get('elevation_gain'),
                elevation_loss=activity_data.get('elevation_loss'),
                elev_high=activity_data.get('elev_high'),
                elev_low=activity_data.get('elev_low'),
                start_date=parse_datetime(activity_data['start_date']) if activity_data.get('start_date') else None,
                start_date_local=parse_datetime(activity_data['start_date_local']) if activity_data.get('start_date_local') else None,
                timezone=activity_data.get('timezone'),
                average_speed=activity_data.get('average_speed'),
                max_speed=activity_data.get('max_speed'),
                average_cadence=activity_data.get('average_cadence'),
                calories=activity_data.get('calories'),
            )
            gpx_filename = activity_data.get('gpx_filename')
            if gpx_filename:
                try:
                    gpx_content = zip_file.read(f'gpx/{gpx_filename}')
                    activity.gpx_file.save(gpx_filename, ContentFile(gpx_content), save=False)
                    summary['gpx_files'] = summary.get('gpx_files', 0) + 1
                except KeyError:
                    pass
            activity.save()
            self._import_images(
                activity_data.get('images') or [],
                zip_file,
                user,
                content_type_activity,
                activity.id,
                summary,
            )
            summary['activities'] = summary.get('activities', 0) + 1

        for image_data in backup_data.get('day_images') or []:
            collection = collection_map.get(image_data.get('collection_export_id'))
            if not collection:
                continue
            day_index = image_data.get('day_index')
            if day_index:
                day = day_map.get((image_data.get('collection_export_id'), day_index))
                if day is None:
                    continue
                parent_type = content_type_day
                parent_id = day.id
            else:
                parent_type = content_type_collection
                parent_id = collection.id
            self._import_images([image_data], zip_file, user, parent_type, parent_id, summary)

    def _serialize_trail_export(self, trail):
        """Export trail data; author fields are optional for backward-compatible backups."""
        data = {
            'name': trail.name,
            'link': trail.link,
            'wanderer_id': trail.wanderer_id,
            'created_at': trail.created_at.isoformat() if trail.created_at else None,
        }
        username = getattr(trail, 'wanderer_author_username', None)
        domain = getattr(trail, 'wanderer_author_domain', None)
        if username:
            data['wanderer_author_username'] = username
        if domain:
            data['wanderer_author_domain'] = domain
        return data

    def _parse_trail_import(self, trail_data):
        """
        Parse trail JSON from backup. Old backups only have name/link/wanderer_id;
        author username/domain are optional and backfilled on read when missing.
        """
        if not isinstance(trail_data, dict):
            return None

        name = self._optional_str(trail_data.get('name'))
        if not name:
            return None

        link = self._optional_str(trail_data.get('link'))
        wanderer_id = self._optional_str(trail_data.get('wanderer_id'))
        if not link and not wanderer_id:
            return None

        domain = self._optional_str(trail_data.get('wanderer_author_domain'))
        if domain:
            domain = domain.lstrip('@')

        return {
            'name': name,
            'link': link,
            'wanderer_id': wanderer_id,
            'wanderer_author_username': self._optional_str(
                trail_data.get('wanderer_author_username')
            ),
            'wanderer_author_domain': domain,
            'created_at': trail_data.get('created_at'),
        }

    def _import_trail(self, user, location, trail_data, trail_name_map, summary):
        parsed = self._parse_trail_import(trail_data)
        if not parsed:
            summary['trails_skipped'] += 1
            return

        create_kwargs = {
            'user': user,
            'location': location,
            'name': parsed['name'],
            'link': parsed['link'],
            'wanderer_id': parsed['wanderer_id'],
            'wanderer_author_username': parsed['wanderer_author_username'],
            'wanderer_author_domain': parsed['wanderer_author_domain'],
        }
        if parsed['created_at']:
            create_kwargs['created_at'] = parsed['created_at']

        try:
            trail = Trail.objects.create(**create_kwargs)
            trail_name_map[(location.id, parsed['name'])] = trail
            summary['trails'] += 1
        except Exception as exc:
            import logging
            logging.warning(
                "Skipped trail import for location %s (%r): %s",
                location.id,
                parsed.get('name'),
                exc,
            )
            summary['trails_skipped'] += 1

    def _serialize_images(self, images_qs):
        """Serialize ContentImage queryset into backup-safe dicts."""
        serialized = []
        for image in images_qs.all():
            lat, lon = point_to_lat_lon(image.coordinates)
            entry = {
                'immich_id': image.immich_id,
                'is_primary': image.is_primary,
                'source': image.source,
                'source_url': image.source_url,
                'latitude': lat,
                'longitude': lon,
                'filename': None,
            }
            if image.image:
                entry['filename'] = image.image.name.split('/')[-1]
            serialized.append(entry)
        return serialized

    def _serialize_attachments(self, attachments_qs):
        """Serialize ContentAttachment queryset into backup-safe dicts."""
        serialized = []
        for attachment in attachments_qs.all():
            entry = {
                'name': attachment.name,
                'filename': None,
            }
            if attachment.file:
                entry['filename'] = attachment.file.name.split('/')[-1]
            serialized.append(entry)
        return serialized

    def _add_storage_file_to_zip(self, zip_file, storage_name, arcname, files_added):
        """Read a Django storage file and add it to the zip once."""
        if not storage_name or storage_name in files_added:
            return

        with default_storage.open(storage_name) as storage_file:
            zip_file.writestr(arcname, storage_file.read())
        files_added.add(storage_name)

    def _import_sharing(self, collection, col_data):
        """Roles for restored members, and guest links. A taken token gets a new one."""
        from django.utils.dateparse import parse_datetime

        for member in col_data.get('members') or []:
            role = member.get('role')
            if role not in CollectionMember.Role.values:
                continue
            CollectionMember.objects.filter(
                collection=collection, user__uuid=member.get('user_uuid')
            ).update(role=role)
        for link in col_data.get('guest_links') or []:
            role = link.get('role')
            if role not in CollectionMember.Role.values:
                continue
            fields = {
                'collection': collection,
                'role': role,
                'label': (link.get('label') or '')[:100],
                'expires_at': parse_datetime(link['expires_at']) if link.get('expires_at') else None,
                'revoked_at': parse_datetime(link['revoked_at']) if link.get('revoked_at') else None,
            }
            token = link.get('token')
            if token and not CollectionGuestLink.objects.filter(token=token).exists():
                fields['token'] = token
            CollectionGuestLink.objects.create(**fields)

    def _import_images(self, images_data, zip_file, user, content_type, object_id, summary):
        created = []
        for img_data in images_data or []:
            img_data = img_data or {}
            immich_id = img_data.get('immich_id')
            explicit_source = img_data.get('source')
            source_url = img_data.get('source_url')
            coordinates = make_point(img_data.get('longitude'), img_data.get('latitude'))
            is_primary = img_data.get('is_primary', False)

            if immich_id:
                created.append(
                    create_content_image(
                        user=user,
                        immich_id=immich_id,
                        is_primary=is_primary,
                        content_type=content_type,
                        object_id=object_id,
                        explicit_source=explicit_source or ContentImage.Source.IMMICH,
                        source_url=source_url,
                        coordinates=coordinates,
                    )
                )
                summary['images'] += 1
                continue

            filename = img_data.get('filename')
            if not filename:
                continue

            try:
                img_content = zip_file.read(f'images/{filename}')
            except KeyError:
                continue

            img_file = ContentFile(img_content, name=filename)
            created.append(
                create_content_image(
                    user=user,
                    image_file=img_file,
                    file_bytes=img_content,
                    is_primary=is_primary,
                    content_type=content_type,
                    object_id=object_id,
                    explicit_source=explicit_source,
                    source_url=source_url,
                    coordinates=coordinates,
                )
            )
            summary['images'] += 1

        return created

    def _import_attachments(self, attachments_data, zip_file, user, content_type, object_id, summary):
        for att_data in attachments_data or []:
            filename = (att_data or {}).get('filename')
            if not filename:
                continue

            try:
                att_content = zip_file.read(f'attachments/{filename}')
            except KeyError:
                continue

            att_file = ContentFile(att_content, name=filename)
            ContentAttachment.objects.create(
                user=user,
                file=att_file,
                name=(att_data or {}).get('name'),
                content_type=content_type,
                object_id=object_id,
            )
            summary['attachments'] += 1
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        Export all user data as a ZIP file containing JSON data and files
        """
        user = request.user
        
        # Build export data structure
        export_data = {
            'version': settings.ADVENTURELOG_RELEASE_VERSION,
            'backup_schema': BACKUP_SCHEMA,
            'export_date': datetime.now().isoformat(),
            'user_email': user.email,
            'user_username': user.username,
            'categories': [],
            'collections': [],
            'locations': [],
            'transportation': [],
            'notes': [],
            'checklists': [],
            'lodging': [],
            'visited_cities': [],
            'visited_regions': [],
            'itinerary_days': [],
            'itinerary_items': [],
            'day_trails': [],
            'day_activities': [],
            'day_images': [],
        }
        visit_id_to_export_ref = {}

        # Export Visited Cities
        for visited_city in user.visitedcity_set.all():
            export_data['visited_cities'].append({
                'city': visited_city.city.id,
            })

        # Export Visited Regions
        for visited_region in user.visitedregion_set.all():
            export_data['visited_regions'].append({
                'region': visited_region.region.id,
            })
        
        # Export Categories
        for category in user.category_set.all():
            export_data['categories'].append({
                'name': category.name,
                'display_name': category.display_name,
                'icon': category.icon,
            })
        
        # Track images so we can reference them for collection primary images
        image_export_map = {}
        collection_id_to_export_id = {}

        # Export Collections
        for idx, collection in enumerate(user.collection_set.all()):
            collection_id_to_export_id[collection.id] = idx
            export_data['collections'].append({
                'export_id': idx,  # Add unique identifier for this export
                'name': collection.name,
                'description': collection.description,
                'is_public': collection.is_public,
                'start_date': collection.start_date.isoformat() if collection.start_date else None,
                'end_date': collection.end_date.isoformat() if collection.end_date else None,
                'type': collection.type,
                'timezone': collection.timezone,
                'is_archived': collection.is_archived,
                'link': collection.link,
                'shared_with_user_ids': [str(uuid) for uuid in collection.shared_with.values_list('uuid', flat=True)],
                'visibility': collection.visibility,
                'story_groups': {name: True for name in Collection.STORY_GROUPS if collection.story_group(name)},
                'members': [
                    {'user_uuid': str(member.user.uuid), 'role': member.role}
                    for member in collection.members.select_related('user')
                ],
                'guest_links': [
                    {
                        'token': link.token,
                        'role': link.role,
                        'label': link.label,
                        'expires_at': link.expires_at.isoformat() if link.expires_at else None,
                        'revoked_at': link.revoked_at.isoformat() if link.revoked_at else None,
                    }
                    for link in collection.guest_links.all()
                ],
            })
            for day in collection.itinerary_days.all().order_by('index', 'date'):
                export_data['itinerary_days'].append({
                    'collection_export_id': idx,
                    'index': day.index,
                    'date': day.date.isoformat() if day.date else None,
                    'name': day.name,
                    'description': day.description,
                })
            self._export_day_files(export_data, collection, idx)
        
        # Create collection name to export_id mapping
        collection_name_to_id = {col.name: idx for idx, col in enumerate(user.collection_set.all())}
        
        # Export locations with related data
        for idx, location in enumerate(user.location_set.all()):
            location_data = {
                'export_id': idx,  # Add unique identifier for this export
                'name': location.name,
                'location': location.location,
                'tags': location.tags,
                'description': location.description,
                'rating': location.rating,
                'price': str(location.price.amount) if location.price else None,
                'price_currency': str(location.price.currency) if location.price else None,
                'link': location.link,
                'is_public': location.is_public,
                'longitude': (
                    str(lon) if (lon := point_to_lat_lon(location.coordinates)[1]) is not None else None
                ),
                'latitude': (
                    str(lat) if (lat := point_to_lat_lon(location.coordinates)[0]) is not None else None
                ),
                'city': location.city_id,
                'region': location.region_id,
                'country': location.country_id,
                # Country PKs are not stable across installs; the ISO code is.
                'country_code': location.country.country_code if location.country_id else None,
                'category_name': location.category.name if location.category else None,
                'collection_export_ids': [collection_name_to_id[col_name] for col_name in location.collections.values_list('name', flat=True) if col_name in collection_name_to_id],
                'visits': [],
                'trails': [],
                'images': [],
                'attachments': []
            }
            
            # Add visits
            for visit_idx, visit in enumerate(location.visits.all()):
                visit_id_to_export_ref[visit.id] = [idx, visit_idx]
                visit_data = {
                    'export_id': visit_idx,  # Add unique identifier for this visit
                    'start_date': visit.start_date.isoformat() if visit.start_date else None,
                    'end_date': visit.end_date.isoformat() if visit.end_date else None,
                    'timezone': visit.timezone,
                    'notes': visit.notes,
                    'activities': [],
                    'images': [],
                    'attachments': [],
                }
                
                # Add activities for this visit
                for activity in visit.activities.all():
                    activity_data = {
                        'name': activity.name,
                        'sport_type': activity.sport_type,
                        'distance': float(activity.distance) if activity.distance else None,
                        'moving_time': activity.moving_time.total_seconds() if activity.moving_time else None,
                        'elapsed_time': activity.elapsed_time.total_seconds() if activity.elapsed_time else None,
                        'rest_time': activity.rest_time.total_seconds() if activity.rest_time else None,
                        'elevation_gain': float(activity.elevation_gain) if activity.elevation_gain else None,
                        'elevation_loss': float(activity.elevation_loss) if activity.elevation_loss else None,
                        'elev_high': float(activity.elev_high) if activity.elev_high else None,
                        'elev_low': float(activity.elev_low) if activity.elev_low else None,
                        'start_date': activity.start_date.isoformat() if activity.start_date else None,
                        'start_date_local': activity.start_date_local.isoformat() if activity.start_date_local else None,
                        'timezone': activity.timezone,
                        'average_speed': float(activity.average_speed) if activity.average_speed else None,
                        'max_speed': float(activity.max_speed) if activity.max_speed else None,
                        'average_cadence': float(activity.average_cadence) if activity.average_cadence else None,
                        'calories': float(activity.calories) if activity.calories else None,
                        'start_lat': (
                            float(s_lat)
                            if (s_lat := point_to_lat_lon(activity.start_point)[0]) is not None
                            else None
                        ),
                        'start_lng': (
                            float(s_lng)
                            if (s_lng := point_to_lat_lon(activity.start_point)[1]) is not None
                            else None
                        ),
                        'end_lat': (
                            float(e_lat)
                            if (e_lat := point_to_lat_lon(activity.end_point)[0]) is not None
                            else None
                        ),
                        'end_lng': (
                            float(e_lng)
                            if (e_lng := point_to_lat_lon(activity.end_point)[1]) is not None
                            else None
                        ),
                        'external_service_id': activity.external_service_id,
                        'trail_name': activity.trail.name if activity.trail else None,  # Link by trail name
                        'gpx_filename': None
                    }
                    
                    # Handle GPX file
                    if activity.gpx_file:
                        activity_data['gpx_filename'] = activity.gpx_file.name.split('/')[-1]
                    
                    visit_data['activities'].append(activity_data)
                
                location_data['visits'].append(visit_data)

                # Add visit images/attachments (generic)
                visit_data['images'] = self._serialize_images(visit.images)
                visit_data['attachments'] = self._serialize_attachments(visit.attachments)

                for image_index, image in enumerate(visit.images.all()):
                    image_export_map[image.id] = {
                        'content_type': 'visit',
                        'location_export_id': idx,
                        'visit_export_id': visit_idx,
                        'image_index': image_index,
                        'immich_id': image.immich_id,
                        'filename': image.image.name.split('/')[-1] if image.image else None,
                    }
            
            # Add trails for this location
            for trail in location.trails.all():
                location_data['trails'].append(self._serialize_trail_export(trail))
            
            # Add images
            location_data['images'] = self._serialize_images(location.images)
            for image_index, image in enumerate(location.images.all()):
                image_export_map[image.id] = {
                    'content_type': 'location',
                    'location_export_id': idx,
                    'image_index': image_index,
                    'immich_id': image.immich_id,
                    'filename': image.image.name.split('/')[-1] if image.image else None,
                }
            
            # Add attachments
            location_data['attachments'] = self._serialize_attachments(location.attachments)
            
            export_data['locations'].append(location_data)

        # Export Transportation
        for idx, transport in enumerate(user.transportation_set.all()):
            collection_export_id = None
            if transport.collection:
                collection_export_id = collection_name_to_id.get(transport.collection.name)
            
            transport_data = {
                'export_id': idx,
                'type': transport.type,
                'name': transport.name,
                'description': transport.description,
                'rating': transport.rating,
                'price': str(transport.price.amount) if transport.price else None,
                'price_currency': str(transport.price.currency) if transport.price else None,
                'link': transport.link,
                'date': transport.date.isoformat() if transport.date else None,
                'end_date': transport.end_date.isoformat() if transport.end_date else None,
                'start_timezone': transport.start_timezone,
                'end_timezone': transport.end_timezone,
                'flight_number': transport.flight_number,
                'from_location': transport.from_location,
                'origin_latitude': (
                    str(o_lat)
                    if (o_lat := point_to_lat_lon(transport.origin)[0]) is not None
                    else None
                ),
                'origin_longitude': (
                    str(o_lon)
                    if (o_lon := point_to_lat_lon(transport.origin)[1]) is not None
                    else None
                ),
                'destination_latitude': (
                    str(d_lat)
                    if (d_lat := point_to_lat_lon(transport.destination)[0]) is not None
                    else None
                ),
                'destination_longitude': (
                    str(d_lon)
                    if (d_lon := point_to_lat_lon(transport.destination)[1]) is not None
                    else None
                ),
                'to_location': transport.to_location,
                'is_public': transport.is_public,
                'collection_export_id': collection_export_id,
                'images': self._serialize_images(transport.images),
                'attachments': self._serialize_attachments(transport.attachments),
            }
            export_data['transportation'].append(transport_data)

            for image_index, image in enumerate(transport.images.all()):
                image_export_map[image.id] = {
                    'content_type': 'transportation',
                    'object_export_id': idx,
                    'image_index': image_index,
                    'immich_id': image.immich_id,
                    'filename': image.image.name.split('/')[-1] if image.image else None,
                }
        
        # Export Notes
        for idx, note in enumerate(user.note_set.all()):
            collection_export_id = None
            if note.collection:
                collection_export_id = collection_name_to_id.get(note.collection.name)
                
            note_data = {
                'export_id': idx,
                'name': note.name,
                'content': note.content,
                'links': note.links,
                'date': note.date.isoformat() if note.date else None,
                'is_public': note.is_public,
                'is_private': note.is_private,
                'collection_export_id': collection_export_id,
                'images': self._serialize_images(note.images),
                'attachments': self._serialize_attachments(note.attachments),
            }
            export_data['notes'].append(note_data)

            for image_index, image in enumerate(note.images.all()):
                image_export_map[image.id] = {
                    'content_type': 'note',
                    'object_export_id': idx,
                    'image_index': image_index,
                    'immich_id': image.immich_id,
                    'filename': image.image.name.split('/')[-1] if image.image else None,
                }
        
        # Export Checklists
        for idx, checklist in enumerate(user.checklist_set.all()):
            collection_export_id = None
            if checklist.collection:
                collection_export_id = collection_name_to_id.get(checklist.collection.name)
                
            checklist_data = {
                'export_id': idx,
                'name': checklist.name,
                'date': checklist.date.isoformat() if checklist.date else None,
                'is_public': checklist.is_public,
                'collection_export_id': collection_export_id,
                'items': []
            }
            
            # Add checklist items
            for item in checklist.checklistitem_set.all():
                checklist_data['items'].append({
                    'name': item.name,
                    'is_checked': item.is_checked,
                    'is_private': item.is_private,
                })
            
            export_data['checklists'].append(checklist_data)
        
        # Export Lodging
        for idx, lodging in enumerate(user.lodging_set.all()):
            collection_export_id = None
            if lodging.collection:
                collection_export_id = collection_name_to_id.get(lodging.collection.name)
            
            lodging_data = {
                'export_id': idx,
                'name': lodging.name,
                'type': lodging.type,
                'description': lodging.description,
                'rating': lodging.rating,
                'link': lodging.link,
                'check_in': lodging.check_in.isoformat() if lodging.check_in else None,
                'check_out': lodging.check_out.isoformat() if lodging.check_out else None,
                'timezone': lodging.timezone,
                'reservation_number': lodging.reservation_number,
                'price': str(lodging.price.amount) if lodging.price else None,
                'price_currency': str(lodging.price.currency) if lodging.price else None,
                'latitude': (
                    str(lat) if (lat := point_to_lat_lon(lodging.coordinates)[0]) is not None else None
                ),
                'longitude': (
                    str(lon) if (lon := point_to_lat_lon(lodging.coordinates)[1]) is not None else None
                ),
                'location': lodging.location,
                'is_public': lodging.is_public,
                'collection_export_id': collection_export_id,
                'images': self._serialize_images(lodging.images),
                'attachments': self._serialize_attachments(lodging.attachments),
            }
            export_data['lodging'].append(lodging_data)

            for image_index, image in enumerate(lodging.images.all()):
                image_export_map[image.id] = {
                    'content_type': 'lodging',
                    'object_export_id': idx,
                    'image_index': image_index,
                    'immich_id': image.immich_id,
                    'filename': image.image.name.split('/')[-1] if image.image else None,
                }

        # Attach collection primary image references (if any)
        for collection in user.collection_set.all():
            export_id = collection_id_to_export_id.get(collection.id)
            if export_id is None:
                continue

            primary = collection.primary_image
            if primary and primary.id in image_export_map:
                export_data['collections'][export_id]['primary_image'] = image_export_map[primary.id]
        
        # Export Itinerary Items
        # Create export_id mappings for all content types
        location_id_to_export_id = {loc.id: idx for idx, loc in enumerate(user.location_set.all())}
        transportation_id_to_export_id = {t.id: idx for idx, t in enumerate(user.transportation_set.all())}
        note_id_to_export_id = {n.id: idx for idx, n in enumerate(user.note_set.all())}
        lodging_id_to_export_id = {l.id: idx for idx, l in enumerate(user.lodging_set.all())}
        checklist_id_to_export_id = {c.id: idx for idx, c in enumerate(user.checklist_set.all())}
        
        for collection_idx, collection in enumerate(user.collection_set.all()):
            for itinerary_item in collection.itinerary_items.select_related('day', 'content_type'):
                content_type_str = itinerary_item.content_type.model
                item_reference = None
                
                # Determine how to reference the item based on content type using export_ids
                if content_type_str == 'location':
                    item_reference = location_id_to_export_id.get(itinerary_item.object_id)
                elif content_type_str == 'transportation':
                    item_reference = transportation_id_to_export_id.get(itinerary_item.object_id)
                elif content_type_str == 'note':
                    item_reference = note_id_to_export_id.get(itinerary_item.object_id)
                elif content_type_str == 'lodging':
                    item_reference = lodging_id_to_export_id.get(itinerary_item.object_id)
                elif content_type_str == 'checklist':
                    item_reference = checklist_id_to_export_id.get(itinerary_item.object_id)
                
                if item_reference is not None:
                    export_data['itinerary_items'].append({
                        'collection_export_id': collection_idx,
                        'content_type': content_type_str,
                        'item_reference': item_reference,
                        'date': itinerary_item.date.isoformat() if itinerary_item.date else None,
                        'is_global': itinerary_item.is_global,
                        'order': itinerary_item.order,
                        'day_index': itinerary_item.day.index if itinerary_item.day_id else None,
                        'span_end_index': itinerary_item.span_end_index,
                        'is_optional': itinerary_item.is_optional,
                        'start_time': itinerary_item.start_time.isoformat() if itinerary_item.start_time else None,
                        'end_time': itinerary_item.end_time.isoformat() if itinerary_item.end_time else None,
                        'timezone': itinerary_item.timezone,
                        'logged_visit_ref': visit_id_to_export_ref.get(itinerary_item.logged_visit_id),
                    })
        
        # Create ZIP file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            with zipfile.ZipFile(tmp_file.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add JSON data
                zip_file.writestr('data.json', json.dumps(export_data, indent=2))
                
                # Add images, attachments, and GPX files
                files_added = set()
                
                for location in user.location_set.all():
                    # Add images
                    for image in location.images.all():
                        if image.image and image.image.name not in files_added:
                            try:
                                filename = image.image.name.split('/')[-1]
                                self._add_storage_file_to_zip(
                                    zip_file,
                                    image.image.name,
                                    f'images/{filename}',
                                    files_added,
                                )
                            except Exception as e:
                                print(f"Error adding image {image.image.name}: {e}")

                    # Add visit images
                    for visit in location.visits.all():
                        for image in visit.images.all():
                            if image.image and image.image.name not in files_added:
                                try:
                                    filename = image.image.name.split('/')[-1]
                                    self._add_storage_file_to_zip(
                                        zip_file,
                                        image.image.name,
                                        f'images/{filename}',
                                        files_added,
                                    )
                                except Exception as e:
                                    print(f"Error adding visit image {image.image.name}: {e}")
                    
                    # Add attachments
                    for attachment in location.attachments.all():
                        if attachment.file and attachment.file.name not in files_added:
                            try:
                                filename = attachment.file.name.split('/')[-1]
                                self._add_storage_file_to_zip(
                                    zip_file,
                                    attachment.file.name,
                                    f'attachments/{filename}',
                                    files_added,
                                )
                            except Exception as e:
                                print(f"Error adding attachment {attachment.file.name}: {e}")

                    # Add visit attachments
                    for visit in location.visits.all():
                        for attachment in visit.attachments.all():
                            if attachment.file and attachment.file.name not in files_added:
                                try:
                                    filename = attachment.file.name.split('/')[-1]
                                    self._add_storage_file_to_zip(
                                        zip_file,
                                        attachment.file.name,
                                        f'attachments/{filename}',
                                        files_added,
                                    )
                                except Exception as e:
                                    print(f"Error adding visit attachment {attachment.file.name}: {e}")
                    
                    # Add GPX files from activities
                    for visit in location.visits.all():
                        for activity in visit.activities.all():
                            if activity.gpx_file and activity.gpx_file.name not in files_added:
                                try:
                                    filename = activity.gpx_file.name.split('/')[-1]
                                    self._add_storage_file_to_zip(
                                        zip_file,
                                        activity.gpx_file.name,
                                        f'gpx/{filename}',
                                        files_added,
                                    )
                                except Exception as e:
                                    print(f"Error adding GPX file {activity.gpx_file.name}: {e}")

                from adventures.utils.day_files import day_file_activities, day_file_images

                for collection in user.collection_set.all():
                    for activity in day_file_activities(collection):
                        if activity.gpx_file and activity.gpx_file.name not in files_added:
                            try:
                                filename = activity.gpx_file.name.split('/')[-1]
                                self._add_storage_file_to_zip(
                                    zip_file,
                                    activity.gpx_file.name,
                                    f'gpx/{filename}',
                                    files_added,
                                )
                            except Exception as e:
                                print(f"Error adding day GPX file {activity.gpx_file.name}: {e}")
                    for image in day_file_images(collection):
                        if image.image and image.image.name not in files_added:
                            try:
                                filename = image.image.name.split('/')[-1]
                                self._add_storage_file_to_zip(
                                    zip_file,
                                    image.image.name,
                                    f'images/{filename}',
                                    files_added,
                                )
                            except Exception as e:
                                print(f"Error adding day image {image.image.name}: {e}")

                # Add non-location content images/attachments
                for transport in user.transportation_set.all():
                    for image in transport.images.all():
                        if image.image and image.image.name not in files_added:
                            try:
                                filename = image.image.name.split('/')[-1]
                                self._add_storage_file_to_zip(
                                    zip_file,
                                    image.image.name,
                                    f'images/{filename}',
                                    files_added,
                                )
                            except Exception as e:
                                print(f"Error adding transportation image {image.image.name}: {e}")
                    for attachment in transport.attachments.all():
                        if attachment.file and attachment.file.name not in files_added:
                            try:
                                filename = attachment.file.name.split('/')[-1]
                                self._add_storage_file_to_zip(
                                    zip_file,
                                    attachment.file.name,
                                    f'attachments/{filename}',
                                    files_added,
                                )
                            except Exception as e:
                                print(f"Error adding transportation attachment {attachment.file.name}: {e}")

                for note in user.note_set.all():
                    for image in note.images.all():
                        if image.image and image.image.name not in files_added:
                            try:
                                filename = image.image.name.split('/')[-1]
                                self._add_storage_file_to_zip(
                                    zip_file,
                                    image.image.name,
                                    f'images/{filename}',
                                    files_added,
                                )
                            except Exception as e:
                                print(f"Error adding note image {image.image.name}: {e}")
                    for attachment in note.attachments.all():
                        if attachment.file and attachment.file.name not in files_added:
                            try:
                                filename = attachment.file.name.split('/')[-1]
                                self._add_storage_file_to_zip(
                                    zip_file,
                                    attachment.file.name,
                                    f'attachments/{filename}',
                                    files_added,
                                )
                            except Exception as e:
                                print(f"Error adding note attachment {attachment.file.name}: {e}")

                for lodging in user.lodging_set.all():
                    for image in lodging.images.all():
                        if image.image and image.image.name not in files_added:
                            try:
                                filename = image.image.name.split('/')[-1]
                                self._add_storage_file_to_zip(
                                    zip_file,
                                    image.image.name,
                                    f'images/{filename}',
                                    files_added,
                                )
                            except Exception as e:
                                print(f"Error adding lodging image {image.image.name}: {e}")
                    for attachment in lodging.attachments.all():
                        if attachment.file and attachment.file.name not in files_added:
                            try:
                                filename = attachment.file.name.split('/')[-1]
                                self._add_storage_file_to_zip(
                                    zip_file,
                                    attachment.file.name,
                                    f'attachments/{filename}',
                                    files_added,
                                )
                            except Exception as e:
                                print(f"Error adding lodging attachment {attachment.file.name}: {e}")
        
        # Return ZIP file as response
        with open(tmp_file.name, 'rb') as zip_file:
            response = HttpResponse(zip_file.read(), content_type='application/zip')
            filename = f"adventurelog_backup_{user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Clean up
        os.unlink(tmp_file.name)
        return response
    
    @action(
        detail=False,
        methods=['post'],
        parser_classes=[MultiPartParser],
        url_path='import',  # changes the URL path to /import
        url_name='import'   # changes the reverse name to 'import'
    )
    def import_data(self, request):
        """
        Import data from a ZIP backup file
        """
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        if 'confirm' not in request.data or request.data['confirm'] != 'yes':
            return Response({'error': 'Confirmation required to proceed with import'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        backup_file = request.FILES['file']
        user = request.user
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            for chunk in backup_file.chunks():
                tmp_file.write(chunk)
            tmp_file_path = tmp_file.name
        
        try:
            with zipfile.ZipFile(tmp_file_path, 'r') as zip_file:
                # Validate backup structure
                if 'data.json' not in zip_file.namelist():
                    return Response({'error': 'Invalid backup file - missing data.json'}, 
                                  status=status.HTTP_400_BAD_REQUEST)
                
                # Load data
                backup_data = json.loads(zip_file.read('data.json').decode('utf-8'))

                try:
                    ensure_backup_schema_supported(backup_data.get('backup_schema'))
                except UnsupportedBackupSchema:
                    return Response(
                        {'error': 'This backup uses a newer schema than this server supports.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                except ValueError:
                    return Response(
                        {'error': 'Invalid backup schema.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                
                # Import with transaction
                with transaction.atomic():
                    # Clear existing data first
                    self._clear_user_data(user)
                    summary = self._import_data(backup_data, zip_file, user)
                
                return Response({
                    'success': True,
                    'message': 'Data imported successfully',
                    'summary': summary
                }, status=status.HTTP_200_OK)
                
        except json.JSONDecodeError:
            return Response({'error': 'Invalid JSON in backup file'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            import logging
            logging.error("Import failed", exc_info=True)
            return Response({'error': 'An internal error occurred during import'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        finally:
            os.unlink(tmp_file_path)
    
    def _clear_user_data(self, user):
        """Clear all existing user data before import"""
        clear_user_adventure_data(user)
    
    def _import_data(self, backup_data, zip_file, user):
        """Import backup data and return summary"""
        from datetime import timedelta
        
        # Track mappings and counts
        category_map = {}
        collection_map = {}  # Map export_id to actual collection object
        location_map = {}    # Map location export_id to actual location object
        trail_name_map = {}  # Map (location_id, trail_name) to trail object
        summary = {
            'categories': 0, 'collections': 0, 'locations': 0,
            'transportation': 0, 'notes': 0, 'checklists': 0,
            'checklist_items': 0, 'lodging': 0, 'images': 0, 
            'attachments': 0, 'visited_cities': 0, 'visited_regions': 0,
            'trails': 0, 'trails_skipped': 0, 'activities': 0, 'gpx_files': 0, 'itinerary_items': 0
        }

        # Import Visited Cities
        for city_data in backup_data.get('visited_cities', []):
            try:
                city_obj = City.objects.get(id=city_data['city'])
                visited_city, created = VisitedCity.objects.get_or_create(user=user, city=city_obj)
                if created:
                    summary['visited_cities'] += 1
            except City.DoesNotExist:
                # If city does not exist, we can skip or log it
                pass

        # Import Visited Regions
        for region_data in backup_data.get('visited_regions', []):
            try:
                region_obj = Region.objects.get(id=region_data['region'])
                visited_region, created = VisitedRegion.objects.get_or_create(user=user, region=region_obj)
                if created:
                    summary['visited_regions'] += 1
            except Region.DoesNotExist:
                # If region does not exist, we can skip or log it
                pass
        
        # Import Categories
        for cat_data in backup_data.get('categories', []):
            category = Category.objects.create(
                user=user,
                name=cat_data['name'],
                display_name=cat_data['display_name'],
                icon=cat_data.get('icon', '🌍')
            )
            category_map[cat_data['name']] = category
            summary['categories'] += 1
        
        pending_primary_images = []
        location_images_map = {}
        visit_images_map = {}
        visit_map = {}
        transportation_images_map = {}
        note_images_map = {}
        lodging_images_map = {}

        content_type_location = ContentType.objects.get(model='location')
        content_type_visit = ContentType.objects.get(model='visit')
        content_type_transportation = ContentType.objects.get(model='transportation')
        content_type_note = ContentType.objects.get(model='note')
        content_type_lodging = ContentType.objects.get(model='lodging')

        # Import Collections
        for col_data in backup_data.get('collections', []):
            collection = Collection.objects.create(
                user=user,
                name=col_data['name'],
                description=col_data.get('description', ''),
                visibility=imported_visibility(backup_data.get('backup_schema'), col_data),
                story_groups=imported_story_groups(
                    backup_data.get('backup_schema'), col_data, Collection.STORY_GROUPS
                ),
                start_date=col_data.get('start_date'),
                end_date=col_data.get('end_date'),
                type=resolve_imported_collection_type(
                    backup_data.get('backup_schema'),
                    col_data.get('start_date'),
                    col_data.get('end_date'),
                    col_data.get('type'),
                ),
                timezone=timezone_or_utc(col_data.get('timezone')),
                is_archived=col_data.get('is_archived', False),
                link=col_data.get('link')
            )
            collection_map[col_data['export_id']] = collection
            summary['collections'] += 1
            
            # Handle shared users
            for uuid in col_data.get('shared_with_user_ids', []):
                try:
                    shared_user = User.objects.get(uuid=uuid)
                    if shared_user.public_profile:
                        collection.shared_with.add(shared_user)
                except User.DoesNotExist:
                    pass
            self._import_sharing(collection, col_data)

            # Defer primary image assignment until images are created
            if col_data.get('primary_image'):
                pending_primary_images.append({
                    'collection_export_id': col_data['export_id'],
                    'data': col_data['primary_image'],
                })
        
        # Import Locations
        for adv_data in backup_data.get('locations', []):

            location_price, location_price_currency = self._parse_money(
                adv_data.get('price'),
                adv_data.get('price_currency')
            )

            city = None
            if adv_data.get('city'):
                try:
                    city = City.objects.get(id=adv_data['city'])
                except City.DoesNotExist:
                    city = None

            region = None
            if adv_data.get('region'):
                try:
                    region = Region.objects.get(id=adv_data['region'])
                except Region.DoesNotExist:
                    region = None

            country = self._resolve_import_country(adv_data, region)

            location = Location(
                user=user,
                name=adv_data['name'],
                location=adv_data.get('location'),
                tags=adv_data.get('tags', []),
                description=adv_data.get('description'),
                rating=adv_data.get('rating'),
                price=location_price,
                price_currency=location_price_currency,
                link=adv_data.get('link'),
                is_public=adv_data.get('is_public', False),
                coordinates=make_point(adv_data.get('longitude'), adv_data.get('latitude')),
                city=city,
                region=region,
                country=country,
                category=category_map.get(adv_data.get('category_name'))
            )
            location.save(_skip_geocode=True)  # Skip geocoding for now
            location_map[adv_data['export_id']] = location
            location_images_map.setdefault(adv_data['export_id'], [])
            
            # Add to collections using export_ids - MUST be done after save()
            for collection_export_id in adv_data.get('collection_export_ids', []):
                if collection_export_id in collection_map:
                    location.collections.add(collection_map[collection_export_id])
            
            # Import trails for this location first
            for trail_data in adv_data.get('trails', []):
                self._import_trail(user, location, trail_data, trail_name_map, summary)
            
            # Import visits and their activities
            for visit_data in adv_data.get('visits', []):
                visit = Visit.objects.create(
                    location=location,
                    start_date=visit_data.get('start_date'),
                    end_date=visit_data.get('end_date'),
                    timezone=visit_data.get('timezone'),
                    notes=visit_data.get('notes')
                )

                visit_export_id = visit_data.get('export_id')
                if visit_export_id is not None:
                    visit_images_map.setdefault((adv_data['export_id'], visit_export_id), [])
                    visit_map[(adv_data['export_id'], visit_export_id)] = visit
                
                # Import activities for this visit
                for activity_data in visit_data.get('activities', []):
                    # Find the trail if specified
                    trail = None
                    if activity_data.get('trail_name'):
                        trail = trail_name_map.get((location.id, activity_data['trail_name']))
                    
                    # Convert time durations back from seconds
                    moving_time = None
                    if activity_data.get('moving_time') is not None:
                        moving_time = timedelta(seconds=activity_data['moving_time'])
                    
                    elapsed_time = None
                    if activity_data.get('elapsed_time') is not None:
                        elapsed_time = timedelta(seconds=activity_data['elapsed_time'])
                    
                    rest_time = None
                    if activity_data.get('rest_time') is not None:
                        rest_time = timedelta(seconds=activity_data['rest_time'])
                    
                    activity = Activity(
                        user=user,
                        visit=visit,
                        trail=trail,
                        name=activity_data['name'],
                        sport_type=activity_data.get('sport_type'),
                        distance=activity_data.get('distance'),
                        moving_time=moving_time,
                        elapsed_time=elapsed_time,
                        rest_time=rest_time,
                        elevation_gain=activity_data.get('elevation_gain'),
                        elevation_loss=activity_data.get('elevation_loss'),
                        elev_high=activity_data.get('elev_high'),
                        elev_low=activity_data.get('elev_low'),
                        start_date=activity_data.get('start_date'),
                        start_date_local=activity_data.get('start_date_local'),
                        timezone=activity_data.get('timezone'),
                        average_speed=activity_data.get('average_speed'),
                        max_speed=activity_data.get('max_speed'),
                        average_cadence=activity_data.get('average_cadence'),
                        calories=activity_data.get('calories'),
                        start_point=make_point(
                            activity_data.get('start_lng'), activity_data.get('start_lat')
                        ),
                        end_point=make_point(
                            activity_data.get('end_lng'), activity_data.get('end_lat')
                        ),
                        external_service_id=activity_data.get('external_service_id')
                    )
                    
                    # Handle GPX file
                    gpx_filename = activity_data.get('gpx_filename')
                    if gpx_filename:
                        try:
                            gpx_content = zip_file.read(f'gpx/{gpx_filename}')
                            gpx_file = ContentFile(gpx_content, name=gpx_filename)
                            activity.gpx_file = gpx_file
                            summary['gpx_files'] += 1
                        except KeyError:
                            pass  # GPX file not found in backup
                    
                    activity.save()
                    summary['activities'] += 1

                # Import visit images/attachments (if present)
                created_visit_images = self._import_images(
                    visit_data.get('images', []),
                    zip_file,
                    user,
                    content_type_visit,
                    visit.id,
                    summary,
                )
                if visit_export_id is not None:
                    visit_images_map[(adv_data['export_id'], visit_export_id)].extend(created_visit_images)

                self._import_attachments(
                    visit_data.get('attachments', []),
                    zip_file,
                    user,
                    content_type_visit,
                    visit.id,
                    summary,
                )
            
            # Import images
            created_location_images = self._import_images(
                adv_data.get('images', []),
                zip_file,
                user,
                content_type_location,
                location.id,
                summary,
            )
            location_images_map[adv_data['export_id']].extend(created_location_images)

            self._import_attachments(
                adv_data.get('attachments', []),
                zip_file,
                user,
                content_type_location,
                location.id,
                summary,
            )
            
            summary['locations'] += 1

        # Import Transportation
        transportation_map = {}  # Map export_id to actual transportation object
        for trans_data in backup_data.get('transportation', []):
            collection = None
            if trans_data.get('collection_export_id') is not None:
                collection = collection_map.get(trans_data['collection_export_id'])

            transport_price, transport_price_currency = self._parse_money(
                trans_data.get('price'),
                trans_data.get('price_currency')
            )
                
            transportation = Transportation.objects.create(
                user=user,
                type=trans_data['type'],
                name=trans_data['name'],
                description=trans_data.get('description'),
                rating=trans_data.get('rating'),
                price=transport_price,
                price_currency=transport_price_currency,
                link=trans_data.get('link'),
                date=trans_data.get('date'),
                end_date=trans_data.get('end_date'),
                start_timezone=trans_data.get('start_timezone'),
                end_timezone=trans_data.get('end_timezone'),
                flight_number=trans_data.get('flight_number'),
                from_location=trans_data.get('from_location'),
                origin=make_point(
                    trans_data.get('origin_longitude'), trans_data.get('origin_latitude')
                ),
                destination=make_point(
                    trans_data.get('destination_longitude'),
                    trans_data.get('destination_latitude'),
                ),
                to_location=trans_data.get('to_location'),
                is_public=trans_data.get('is_public', False),
                collection=collection
            )

            export_id = trans_data.get('export_id')
            if export_id is not None:
                transportation_images_map.setdefault(export_id, [])
                transportation_images_map[export_id].extend(
                    self._import_images(
                        trans_data.get('images', []),
                        zip_file,
                        user,
                        content_type_transportation,
                        transportation.id,
                        summary,
                    )
                )
                self._import_attachments(
                    trans_data.get('attachments', []),
                    zip_file,
                    user,
                    content_type_transportation,
                    transportation.id,
                    summary,
                )
            # Only add to map if export_id exists (for backward compatibility with old backups)
            if 'export_id' in trans_data:
                transportation_map[trans_data['export_id']] = transportation
            summary['transportation'] += 1
        
        # Import Notes
        note_map = {}  # Map export_id to actual note object
        for note_data in backup_data.get('notes', []):
            collection = None
            if note_data.get('collection_export_id') is not None:
                collection = collection_map.get(note_data['collection_export_id'])
                
            note = Note.objects.create(
                user=user,
                name=note_data['name'],
                content=note_data.get('content'),
                links=note_data.get('links', []),
                date=note_data.get('date'),
                is_public=note_data.get('is_public', False),
                is_private=bool(note_data.get('is_private', False)),
                collection=collection
            )

            export_id = note_data.get('export_id')
            if export_id is not None:
                note_images_map.setdefault(export_id, [])
                note_images_map[export_id].extend(
                    self._import_images(
                        note_data.get('images', []),
                        zip_file,
                        user,
                        content_type_note,
                        note.id,
                        summary,
                    )
                )
                self._import_attachments(
                    note_data.get('attachments', []),
                    zip_file,
                    user,
                    content_type_note,
                    note.id,
                    summary,
                )
            # Only add to map if export_id exists (for backward compatibility with old backups)
            if 'export_id' in note_data:
                note_map[note_data['export_id']] = note
            summary['notes'] += 1
        
        # Import Checklists
        checklist_map = {}  # Map export_id to actual checklist object
        for check_data in backup_data.get('checklists', []):
            collection = None
            if check_data.get('collection_export_id') is not None:
                collection = collection_map.get(check_data['collection_export_id'])
                
            checklist = Checklist.objects.create(
                user=user,
                name=check_data['name'],
                date=check_data.get('date'),
                is_public=check_data.get('is_public', False),
                collection=collection
            )
            
            # Import checklist items
            for item_data in check_data.get('items', []):
                ChecklistItem.objects.create(
                    user=user,
                    checklist=checklist,
                    name=item_data['name'],
                    is_checked=item_data.get('is_checked', False),
                    is_private=bool(item_data.get('is_private', False)),
                )
                summary['checklist_items'] += 1
            
            # Only add to map if export_id exists (for backward compatibility with old backups)
            if 'export_id' in check_data:
                checklist_map[check_data['export_id']] = checklist
            summary['checklists'] += 1
        
        # Import Lodging
        lodging_map = {}  # Map export_id to actual lodging object
        for lodg_data in backup_data.get('lodging', []):
            collection = None
            if lodg_data.get('collection_export_id') is not None:
                collection = collection_map.get(lodg_data['collection_export_id'])

            lodging_price, lodging_price_currency = self._parse_money(
                lodg_data.get('price'),
                lodg_data.get('price_currency')
            )
                
            lodging = Lodging.objects.create(
                user=user,
                name=lodg_data['name'],
                type=lodg_data.get('type', 'other'),
                description=lodg_data.get('description'),
                rating=lodg_data.get('rating'),
                link=lodg_data.get('link'),
                check_in=lodg_data.get('check_in'),
                check_out=lodg_data.get('check_out'),
                timezone=lodg_data.get('timezone'),
                reservation_number=lodg_data.get('reservation_number'),
                price=lodging_price,
                price_currency=lodging_price_currency,
                coordinates=make_point(lodg_data.get('longitude'), lodg_data.get('latitude')),
                location=lodg_data.get('location'),
                is_public=lodg_data.get('is_public', False),
                collection=collection
            )

            export_id = lodg_data.get('export_id')
            if export_id is not None:
                lodging_images_map.setdefault(export_id, [])
                lodging_images_map[export_id].extend(
                    self._import_images(
                        lodg_data.get('images', []),
                        zip_file,
                        user,
                        content_type_lodging,
                        lodging.id,
                        summary,
                    )
                )
                self._import_attachments(
                    lodg_data.get('attachments', []),
                    zip_file,
                    user,
                    content_type_lodging,
                    lodging.id,
                    summary,
                )
            # Only add to map if export_id exists (for backward compatibility with old backups)
            if 'export_id' in lodg_data:
                lodging_map[lodg_data['export_id']] = lodging
            summary['lodging'] += 1

        # Apply primary image selections now that images exist
        for entry in pending_primary_images:
            collection = collection_map.get(entry['collection_export_id'])
            data = entry.get('data', {}) or {}
            if not collection:
                continue

            content_type_str = data.get('content_type') or 'location'
            img_index = data.get('image_index')
            if img_index is None:
                continue

            if content_type_str == 'location':
                loc_export_id = data.get('location_export_id')
                if loc_export_id is None:
                    continue
                images_for_object = location_images_map.get(loc_export_id, [])
            elif content_type_str == 'visit':
                loc_export_id = data.get('location_export_id')
                visit_export_id = data.get('visit_export_id')
                if loc_export_id is None or visit_export_id is None:
                    continue
                images_for_object = visit_images_map.get((loc_export_id, visit_export_id), [])
            elif content_type_str == 'transportation':
                obj_export_id = data.get('object_export_id')
                if obj_export_id is None:
                    continue
                images_for_object = transportation_images_map.get(obj_export_id, [])
            elif content_type_str == 'note':
                obj_export_id = data.get('object_export_id')
                if obj_export_id is None:
                    continue
                images_for_object = note_images_map.get(obj_export_id, [])
            elif content_type_str == 'lodging':
                obj_export_id = data.get('object_export_id')
                if obj_export_id is None:
                    continue
                images_for_object = lodging_images_map.get(obj_export_id, [])
            else:
                continue

            if 0 <= img_index < len(images_for_object):
                collection.primary_image = images_for_object[img_index]
                collection.save(update_fields=['primary_image'])
        
        has_day_plan = backup_has_day_plan(backup_data.get('backup_schema'))

        # Import itinerary days (schema 3). Older files only stored placements by date.
        day_map = {}
        if has_day_plan:
            for day_data in backup_data.get('itinerary_days', []):
                collection = collection_map.get(day_data.get('collection_export_id'))
                if not collection:
                    continue
                day = CollectionItineraryDay.objects.create(
                    collection=collection,
                    index=day_data.get('index'),
                    date=day_data.get('date'),
                    name=day_data.get('name'),
                    description=day_data.get('description'),
                )
                if day.index is not None:
                    day_map[(day_data.get('collection_export_id'), day.index)] = day

            self._import_day_files(backup_data, zip_file, user, collection_map, day_map, summary)

        # Import Itinerary Items
        # Maps already created during import of each content type
        
        for itinerary_data in backup_data.get('itinerary_items', []):
            collection = collection_map.get(itinerary_data['collection_export_id'])
            if not collection:
                continue
            
            content_type_str = itinerary_data['content_type']
            item_reference = itinerary_data['item_reference']
            
            # Get the actual object based on content type
            content_object = None
            content_type = None
            
            if content_type_str == 'location':
                content_object = location_map.get(item_reference)  # item_reference is export_id
                content_type = ContentType.objects.get(model='location')
            elif content_type_str == 'transportation':
                content_object = transportation_map.get(item_reference)  # item_reference is export_id
                content_type = ContentType.objects.get(model='transportation')
            elif content_type_str == 'note':
                content_object = note_map.get(item_reference)  # item_reference is export_id
                content_type = ContentType.objects.get(model='note')
            elif content_type_str == 'lodging':
                content_object = lodging_map.get(item_reference)  # item_reference is export_id
                content_type = ContentType.objects.get(model='lodging')
            elif content_type_str == 'checklist':
                content_object = checklist_map.get(item_reference)  # item_reference is export_id
                content_type = ContentType.objects.get(model='checklist')
            
            if content_object and content_type:
                is_global = bool(itinerary_data.get('is_global', False))
                day = None
                placement = {}
                if has_day_plan:
                    day = day_map.get((itinerary_data['collection_export_id'], itinerary_data.get('day_index')))
                    logged_ref = itinerary_data.get('logged_visit_ref')
                    placement = {
                        'span_end_index': itinerary_data.get('span_end_index') if day else None,
                        'is_optional': bool(itinerary_data.get('is_optional', False)),
                        'start_time': itinerary_data.get('start_time'),
                        'end_time': itinerary_data.get('end_time'),
                        'timezone': itinerary_data.get('timezone'),
                        'logged_visit': visit_map.get(tuple(logged_ref)) if logged_ref else None,
                    }
                CollectionItineraryItem.objects.create(
                    collection=collection,
                    content_type=content_type,
                    object_id=content_object.id,
                    day=day,
                    date=itinerary_data.get('date') if not is_global else None,
                    is_global=is_global,
                    order=itinerary_data['order'],
                    **placement,
                )
                summary['itinerary_items'] += 1

        # Schema 2 and older: run the day-plan conversion once per trip.
        if not has_day_plan:
            for collection in collection_map.values():
                if collection.type == 'trip':
                    collection.refresh_from_db()
                    convert_collection(collection)
        
        return summary