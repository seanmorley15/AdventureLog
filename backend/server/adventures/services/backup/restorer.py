"""Creating records from the JSON and files of a backup.

The same restorer reads a whole-account backup (which replaces what the user had, so the
caller clears it first) and a collection archive (which adds one collection next to
what the user already has). The options say which.
"""

import logging
from dataclasses import dataclass, field
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.utils.dateparse import parse_datetime

from adventures.models import (
    Activity, Category, Checklist, ChecklistItem, Collection, CollectionComment,
    CollectionGuestLink, CollectionInvite, CollectionItineraryDay, CollectionItineraryItem,
    CollectionMember, ContentAttachment, ContentImage, Location, Lodging, Note, Trail,
    Transportation, Visit,
)
from adventures.services.images.metadata import create_content_image
from adventures.services.locations.matching import find_best_duplicate_location
from adventures.services import day_plan
from adventures.utils.collection_type import (
    backup_has_comments,
    backup_has_day_plan,
    imported_story_groups,
    imported_visibility,
    resolve_imported_collection_type,
)
from core.geo import make_point
from core.timezones import timezone_or_utc
from worldtravel.models import City, Region
from worldtravel.services import mark_cities_visited, mark_regions_visited

from . import serialization as ser

logger = logging.getLogger(__name__)
User = get_user_model()

CREATE_NEW_LOCATIONS = 'create'
LINK_EXISTING_LOCATIONS = 'link'
EXISTING_LOCATION_CHOICES = (CREATE_NEW_LOCATIONS, LINK_EXISTING_LOCATIONS)


@dataclass
class RestoreOptions:
    # Rename a restored collection ("Trip (1)") when the user already has one with that name.
    unique_collection_names: bool = False
    # 'link' reuses a place the user already has instead of creating a second copy of it.
    existing_locations: str = CREATE_NEW_LOCATIONS


@dataclass
class RestoreResult:
    summary: dict
    collections: list = field(default_factory=list)


def _new_summary():
    return {
        'categories': 0, 'collections': 0, 'locations': 0,
        'transportation': 0, 'notes': 0, 'checklists': 0,
        'checklist_items': 0, 'lodging': 0, 'images': 0,
        'attachments': 0, 'visited_cities': 0, 'visited_regions': 0,
        'trails': 0, 'trails_skipped': 0, 'activities': 0, 'gpx_files': 0, 'itinerary_items': 0,
    }


def _seconds(value):
    return timedelta(seconds=float(value)) if value not in (None, '') else None


class BackupRestorer:
    def __init__(self, data, archive, user, options=None):
        self.data = data
        self.archive = archive
        self.user = user
        self.options = options or RestoreOptions()
        self.schema = data.get('backup_schema')
        self.summary = _new_summary()
        if self.options.existing_locations == LINK_EXISTING_LOCATIONS:
            self.summary['locations_linked'] = 0

        self.categories = {}
        self.collections = {}      # export id -> Collection
        self.guest_links = {}      # collection export id -> {exported guest token: restored link}
        self.locations = {}        # export id -> Location
        self.visits = {}           # (location export id, visit export id) -> Visit
        self.trails = {}           # (location id, trail name) -> Trail
        self.transportation = {}
        self.notes = {}
        self.checklists = {}
        self.lodging = {}
        self.days = {}             # (collection export id, day index) -> CollectionItineraryDay
        self.images = {            # created photos by export id, for choosing a collection's cover
            'location': {}, 'visit': {}, 'transportation': {}, 'note': {}, 'lodging': {},
        }
        self.placements = {}       # position in itinerary_items -> CollectionItineraryItem
        self.pending_covers = []

    def restore(self):
        self._visited_geography()
        self._categories()
        self._collections()
        self._locations()
        self._transportation()
        self._notes()
        self._checklists()
        self._lodging()
        self._covers()
        has_day_plan = backup_has_day_plan(self.schema)
        if has_day_plan:
            self._days()
        self._itinerary_items(has_day_plan)
        if backup_has_comments(self.schema):
            self._comments()
        if not has_day_plan:
            self._build_day_plans()
        return RestoreResult(self.summary, list(self.collections.values()))

    # ---- geography and categories

    def _visited_geography(self):
        for city_data in self.data.get('visited_cities', []):
            try:
                city = City.objects.get(id=city_data['city'])
            except City.DoesNotExist:
                continue
            if mark_cities_visited(self.user.id, [city.id]):
                self.summary['visited_cities'] += 1

        for region_data in self.data.get('visited_regions', []):
            try:
                region = Region.objects.get(id=region_data['region'])
            except Region.DoesNotExist:
                continue
            if mark_regions_visited(self.user.id, [region.id]):
                self.summary['visited_regions'] += 1

    def _categories(self):
        for cat_data in self.data.get('categories', []):
            category, _ = Category.objects.get_or_create(
                user=self.user,
                name=cat_data['name'],
                defaults={
                    'display_name': cat_data['display_name'],
                    'icon': cat_data.get('icon', '🌍'),
                },
            )
            self.categories[cat_data['name']] = category
            self.summary['categories'] += 1

    # ---- collections and sharing

    def _unique_collection_name(self, name):
        existing = set(Collection.objects.filter(user=self.user).values_list('name', flat=True))
        if name not in existing:
            return name
        number = 1
        while f'{name} ({number})' in existing:
            number += 1
        return f'{name} ({number})'

    def _collections(self):
        for col_data in self.data.get('collections', []):
            name = col_data['name']
            if self.options.unique_collection_names:
                name = self._unique_collection_name(name)
            collection = Collection.objects.create(
                user=self.user,
                name=name,
                description=col_data.get('description', ''),
                visibility=imported_visibility(self.schema, col_data),
                # Comments stay off unless a schema 6 file turned them on.
                comment_access=(
                    col_data.get('comment_access')
                    if backup_has_comments(self.schema)
                    and col_data.get('comment_access') in Collection.CommentAccess.values
                    else Collection.CommentAccess.OFF
                ),
                story_groups=imported_story_groups(self.schema, col_data, Collection.STORY_GROUPS),
                start_date=col_data.get('start_date'),
                end_date=col_data.get('end_date'),
                type=resolve_imported_collection_type(
                    self.schema, col_data.get('start_date'), col_data.get('end_date'), col_data.get('type'),
                ),
                timezone=timezone_or_utc(col_data.get('timezone')),
                is_archived=col_data.get('is_archived', False),
                link=col_data.get('link'),
            )
            self.collections[col_data['export_id']] = collection
            self.summary['collections'] += 1
            self.guest_links[col_data['export_id']] = self._sharing(
                collection, col_data, col_data.get('shared_with_user_ids', [])
            )
            # The cover is chosen once its photo exists.
            if col_data.get('primary_image'):
                self.pending_covers.append((col_data['export_id'], col_data['primary_image']))

    def _sharing(self, collection, col_data, shared_user_uuids=()):
        """
        Invite the people a collection was shared with, and restore its guest links.

        A file cannot add someone to a collection: restored members come back as pending
        invites that they accept, as with any other share. Guest links get fresh tokens, so a
        file cannot choose the secret that opens a collection. Returns ``{exported token:
        restored link}`` so guest comments can be re-linked.
        """
        roles = {}
        for member in col_data.get('members') or []:
            if member.get('role') in CollectionMember.Role.values:
                roles[str(member.get('user_uuid'))] = member['role']
        invitees = [str(uuid) for uuid in shared_user_uuids]
        invitees += [uuid for uuid in roles if uuid not in invitees]
        for uuid in invitees:
            invited = User.objects.filter(uuid=uuid, public_profile=True).exclude(pk=collection.user_id).first()
            if invited is None:
                continue
            CollectionInvite.objects.get_or_create(
                collection=collection,
                invited_user=invited,
                defaults={'role': roles.get(uuid, CollectionMember.Role.EDITOR)},
            )

        restored = {}
        for link in col_data.get('guest_links') or []:
            role = link.get('role')
            if role not in CollectionMember.Role.values:
                continue
            created = CollectionGuestLink.objects.create(
                collection=collection,
                role=role,
                label=(link.get('label') or '')[:100],
                expires_at=parse_datetime(link['expires_at']) if link.get('expires_at') else None,
                revoked_at=parse_datetime(link['revoked_at']) if link.get('revoked_at') else None,
            )
            if link.get('token'):
                restored[link['token']] = created
        return restored

    # ---- places

    def _existing_location(self, adv_data):
        if self.options.existing_locations != LINK_EXISTING_LOCATIONS:
            return None
        return find_best_duplicate_location(
            self.user,
            name=adv_data.get('name') or 'Untitled',
            latitude=adv_data.get('latitude'),
            longitude=adv_data.get('longitude'),
            location=adv_data.get('location'),
        )

    def _link_to_collections(self, location, adv_data):
        # Must come after save(): a many-to-many link needs a saved row.
        for collection_export_id in adv_data.get('collection_export_ids', []):
            if collection_export_id in self.collections:
                location.collections.add(self.collections[collection_export_id])

    def _locations(self):
        for adv_data in self.data.get('locations', []):
            export_id = adv_data['export_id']

            existing = self._existing_location(adv_data)
            if existing is not None:
                # What the user already has is left as it is: no second copy, no extra photos.
                self.locations[export_id] = existing
                self.images['location'].setdefault(export_id, [])
                self._link_to_collections(existing, adv_data)
                self.summary['locations_linked'] += 1
                continue

            price, price_currency = ser.parse_money(adv_data.get('price'), adv_data.get('price_currency'))

            city = City.objects.filter(id=adv_data['city']).first() if adv_data.get('city') else None
            region = Region.objects.filter(id=adv_data['region']).first() if adv_data.get('region') else None
            country = ser.resolve_import_country(adv_data, region)

            location = Location(
                user=self.user,
                name=adv_data['name'],
                location=adv_data.get('location'),
                tags=adv_data.get('tags', []),
                description=adv_data.get('description'),
                rating=adv_data.get('rating'),
                price=price,
                price_currency=price_currency,
                link=adv_data.get('link'),
                is_public=adv_data.get('is_public', False),
                coordinates=make_point(adv_data.get('longitude'), adv_data.get('latitude')),
                city=city,
                region=region,
                country=country,
                category=self.categories.get(adv_data.get('category_name')),
            )
            location.save(_skip_geocode=True)  # Geocoding is slow, and the file already has the geography
            self.locations[export_id] = location
            self.images['location'].setdefault(export_id, [])
            self._link_to_collections(location, adv_data)

            for trail_data in adv_data.get('trails', []):
                self._trail(location, trail_data)
            for visit_data in adv_data.get('visits', []):
                self._visit(location, export_id, visit_data)

            self.images['location'][export_id].extend(
                self._images(adv_data.get('images', []), ContentType.objects.get_for_model(Location), location.id)
            )
            self._attachments(adv_data.get('attachments', []), ContentType.objects.get_for_model(Location), location.id)
            self.summary['locations'] += 1

    def _trail(self, location, trail_data):
        parsed = ser.parse_trail(trail_data)
        if not parsed:
            self.summary['trails_skipped'] += 1
            return

        create_kwargs = {
            'user': self.user,
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
        except Exception as exc:
            logger.warning(
                'Skipped trail import for location %s (%r): %s', location.id, parsed.get('name'), exc
            )
            self.summary['trails_skipped'] += 1
            return
        self.trails[(location.id, parsed['name'])] = trail
        self._images(trail_data.get('images') or [], ContentType.objects.get_for_model(Trail), trail.id)
        self.summary['trails'] += 1

    def _visit(self, location, location_export_id, visit_data):
        visit = Visit.objects.create(
            location=location,
            start_date=visit_data.get('start_date'),
            end_date=visit_data.get('end_date'),
            timezone=visit_data.get('timezone'),
            notes=visit_data.get('notes'),
        )

        visit_export_id = visit_data.get('export_id')
        key = (location_export_id, visit_export_id)
        if visit_export_id is not None:
            self.images['visit'].setdefault(key, [])
            self.visits[key] = visit

        for activity_data in visit_data.get('activities', []):
            self._visit_activity(location, visit, activity_data)

        created = self._images(visit_data.get('images', []), ContentType.objects.get_for_model(Visit), visit.id)
        if visit_export_id is not None:
            self.images['visit'][key].extend(created)
        self._attachments(visit_data.get('attachments', []), ContentType.objects.get_for_model(Visit), visit.id)

    def _visit_activity(self, location, visit, activity_data):
        trail = None
        if activity_data.get('trail_name'):
            trail = self.trails.get((location.id, activity_data['trail_name']))

        activity = Activity(
            user=self.user,
            visit=visit,
            trail=trail,
            name=activity_data['name'],
            sport_type=activity_data.get('sport_type'),
            distance=activity_data.get('distance'),
            moving_time=timedelta(seconds=activity_data['moving_time']) if activity_data.get('moving_time') is not None else None,
            elapsed_time=timedelta(seconds=activity_data['elapsed_time']) if activity_data.get('elapsed_time') is not None else None,
            rest_time=timedelta(seconds=activity_data['rest_time']) if activity_data.get('rest_time') is not None else None,
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
            start_point=make_point(activity_data.get('start_lng'), activity_data.get('start_lat')),
            end_point=make_point(activity_data.get('end_lng'), activity_data.get('end_lat')),
            external_service_id=activity_data.get('external_service_id'),
        )

        gpx_filename = activity_data.get('gpx_filename')
        if gpx_filename:
            try:
                activity.gpx_file = ContentFile(self.archive.read(f'gpx/{gpx_filename}'), name=gpx_filename)
                self.summary['gpx_files'] += 1
            except KeyError:
                pass  # The GPX file is not in the archive.

        activity.save()
        self._images(activity_data.get('images') or [], ContentType.objects.get_for_model(Activity), activity.id)
        self.summary['activities'] += 1

    # ---- records that live in a collection

    def _collection_of(self, data):
        export_id = data.get('collection_export_id')
        return self.collections.get(export_id) if export_id is not None else None

    def _transportation(self):
        content_type = ContentType.objects.get_for_model(Transportation)
        for data in self.data.get('transportation', []):
            price, price_currency = ser.parse_money(data.get('price'), data.get('price_currency'))
            transportation = Transportation.objects.create(
                user=self.user,
                type=data['type'],
                name=data['name'],
                description=data.get('description'),
                rating=data.get('rating'),
                price=price,
                price_currency=price_currency,
                link=data.get('link'),
                date=data.get('date'),
                end_date=data.get('end_date'),
                start_timezone=data.get('start_timezone'),
                end_timezone=data.get('end_timezone'),
                flight_number=data.get('flight_number'),
                start_code=data.get('start_code'),
                end_code=data.get('end_code'),
                from_location=data.get('from_location'),
                origin=make_point(data.get('origin_longitude'), data.get('origin_latitude')),
                destination=make_point(data.get('destination_longitude'), data.get('destination_latitude')),
                to_location=data.get('to_location'),
                is_public=data.get('is_public', False),
                collection=self._collection_of(data),
            )
            self._restore_media(data, 'transportation', content_type, transportation, self.transportation)
            self.summary['transportation'] += 1

    def _notes(self):
        content_type = ContentType.objects.get_for_model(Note)
        for data in self.data.get('notes', []):
            note = Note.objects.create(
                user=self.user,
                name=data['name'],
                content=data.get('content'),
                links=data.get('links', []),
                date=data.get('date'),
                is_public=data.get('is_public', False),
                is_private=bool(data.get('is_private', False)),
                collection=self._collection_of(data),
            )
            self._restore_media(data, 'note', content_type, note, self.notes)
            self.summary['notes'] += 1

    def _checklists(self):
        for data in self.data.get('checklists', []):
            checklist = Checklist.objects.create(
                user=self.user,
                name=data['name'],
                date=data.get('date'),
                is_public=data.get('is_public', False),
                collection=self._collection_of(data),
            )
            for item_data in data.get('items', []):
                ChecklistItem.objects.create(
                    user=self.user,
                    checklist=checklist,
                    name=item_data['name'],
                    is_checked=item_data.get('is_checked', False),
                    is_private=bool(item_data.get('is_private', False)),
                )
                self.summary['checklist_items'] += 1
            # Old backups have no export ids.
            if 'export_id' in data:
                self.checklists[data['export_id']] = checklist
            self.summary['checklists'] += 1

    def _lodging(self):
        content_type = ContentType.objects.get_for_model(Lodging)
        for data in self.data.get('lodging', []):
            price, price_currency = ser.parse_money(data.get('price'), data.get('price_currency'))
            lodging = Lodging.objects.create(
                user=self.user,
                name=data['name'],
                type=data.get('type', 'other'),
                description=data.get('description'),
                rating=data.get('rating'),
                link=data.get('link'),
                check_in=data.get('check_in'),
                check_out=data.get('check_out'),
                timezone=data.get('timezone'),
                reservation_number=data.get('reservation_number'),
                price=price,
                price_currency=price_currency,
                coordinates=make_point(data.get('longitude'), data.get('latitude')),
                location=data.get('location'),
                is_public=data.get('is_public', False),
                collection=self._collection_of(data),
            )
            self._restore_media(data, 'lodging', content_type, lodging, self.lodging)
            self.summary['lodging'] += 1

    def _restore_media(self, data, kind, content_type, record, registry):
        """Photos and attachments of a record, then remember it by export id for placements."""
        export_id = data.get('export_id')
        if export_id is not None:
            self.images[kind].setdefault(export_id, []).extend(
                self._images(data.get('images', []), content_type, record.id)
            )
            self._attachments(data.get('attachments', []), content_type, record.id)
            registry[export_id] = record

    # ---- photos and attachments

    def _images(self, images_data, content_type, object_id):
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
                        user=self.user,
                        immich_id=immich_id,
                        is_primary=is_primary,
                        content_type=content_type,
                        object_id=object_id,
                        explicit_source=explicit_source or ContentImage.Source.IMMICH,
                        source_url=source_url,
                        coordinates=coordinates,
                    )
                )
                self.summary['images'] += 1
                continue

            filename = img_data.get('filename')
            if not filename:
                continue
            try:
                content = self.archive.read(f'images/{filename}')
            except KeyError:
                continue

            created.append(
                create_content_image(
                    user=self.user,
                    image_file=ContentFile(content, name=filename),
                    file_bytes=content,
                    is_primary=is_primary,
                    content_type=content_type,
                    object_id=object_id,
                    explicit_source=explicit_source,
                    source_url=source_url,
                    coordinates=coordinates,
                )
            )
            self.summary['images'] += 1
        return created

    def _attachments(self, attachments_data, content_type, object_id):
        for att_data in attachments_data or []:
            filename = (att_data or {}).get('filename')
            if not filename:
                continue
            try:
                content = self.archive.read(f'attachments/{filename}')
            except KeyError:
                continue
            ContentAttachment.objects.create(
                user=self.user,
                file=ContentFile(content, name=filename),
                name=(att_data or {}).get('name'),
                content_type=content_type,
                object_id=object_id,
            )
            self.summary['attachments'] += 1

    def _covers(self):
        """Pick each collection's cover now that the photos exist."""
        for collection_export_id, ref in self.pending_covers:
            collection = self.collections.get(collection_export_id)
            ref = ref or {}
            if not collection:
                continue

            kind = ref.get('content_type') or 'location'
            image_index = ref.get('image_index')
            if image_index is None:
                continue

            if kind == 'location':
                key = ref.get('location_export_id')
                images = self.images['location'].get(key, []) if key is not None else None
            elif kind == 'visit':
                location_id, visit_id = ref.get('location_export_id'), ref.get('visit_export_id')
                images = (
                    self.images['visit'].get((location_id, visit_id), [])
                    if location_id is not None and visit_id is not None else None
                )
            elif kind in ('transportation', 'note', 'lodging'):
                key = ref.get('object_export_id')
                images = self.images[kind].get(key, []) if key is not None else None
            else:
                images = None

            if images is not None and 0 <= image_index < len(images):
                collection.primary_image = images[image_index]
                collection.save(update_fields=['primary_image'])

    # ---- day plan

    def _days(self):
        """Schema 3 and later store the days. Older files only stored placements by date."""
        for day_data in self.data.get('itinerary_days', []):
            collection = self.collections.get(day_data.get('collection_export_id'))
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
                self.days[(day_data.get('collection_export_id'), day.index)] = day
        self._day_files()

    def _day_files(self):
        """Schema 4: trails, activities, and photos whose parent is a day or Ideas."""
        trail_ids = {}
        trail_type = ContentType.objects.get_for_model(Trail)
        activity_type = ContentType.objects.get_for_model(Activity)
        day_type = ContentType.objects.get_for_model(CollectionItineraryDay)
        collection_type = ContentType.objects.get_for_model(Collection)

        def parent_of(item):
            """(collection, day) for a day file, or None when its collection or day is missing."""
            export_id = item.get('collection_export_id')
            collection = self.collections.get(export_id)
            if not collection:
                return None
            day_index = item.get('day_index')
            day = self.days.get((export_id, day_index)) if day_index else None
            if day_index and day is None:
                return None
            return collection, day

        for trail_data in self.data.get('day_trails') or []:
            parent = parent_of(trail_data)
            if parent is None:
                continue
            collection, day = parent
            parsed = ser.parse_trail(trail_data)
            if not parsed:
                self.summary['trails_skipped'] = self.summary.get('trails_skipped', 0) + 1
                continue
            trail = Trail.objects.create(
                user=self.user,
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
            trail_ids[trail_data.get('export_id')] = trail
            self._images(trail_data.get('images') or [], trail_type, trail.id)
            self.summary['trails'] = self.summary.get('trails', 0) + 1

        for activity_data in self.data.get('day_activities') or []:
            parent = parent_of(activity_data)
            if parent is None:
                continue
            collection, day = parent
            activity = Activity(
                user=self.user,
                visit=None,
                day=day,
                collection=None if day else collection,
                trail=trail_ids.get(activity_data.get('trail_export_id')),
                name=activity_data.get('name') or 'Activity',
                sport_type=activity_data.get('sport_type') or 'General',
                distance=activity_data.get('distance'),
                moving_time=_seconds(activity_data.get('moving_time')),
                elapsed_time=_seconds(activity_data.get('elapsed_time')),
                rest_time=_seconds(activity_data.get('rest_time')),
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
                start_point=make_point(activity_data.get('start_lng'), activity_data.get('start_lat')),
                end_point=make_point(activity_data.get('end_lng'), activity_data.get('end_lat')),
                external_service_id=activity_data.get('external_service_id'),
            )
            gpx_filename = activity_data.get('gpx_filename')
            if gpx_filename:
                try:
                    activity.gpx_file.save(
                        gpx_filename, ContentFile(self.archive.read(f'gpx/{gpx_filename}')), save=False
                    )
                    self.summary['gpx_files'] = self.summary.get('gpx_files', 0) + 1
                except KeyError:
                    pass
            activity.save()
            self._images(activity_data.get('images') or [], activity_type, activity.id)
            self.summary['activities'] = self.summary.get('activities', 0) + 1

        for image_data in self.data.get('day_images') or []:
            parent = parent_of(image_data)
            if parent is None:
                continue
            collection, day = parent
            if day is not None:
                self._images([image_data], day_type, day.id)
            else:
                self._images([image_data], collection_type, collection.id)

    def _itinerary_items(self, has_day_plan):
        registries = {
            'location': self.locations,
            'transportation': self.transportation,
            'note': self.notes,
            'lodging': self.lodging,
            'checklist': self.checklists,
        }
        for position, data in enumerate(self.data.get('itinerary_items', [])):
            collection = self.collections.get(data['collection_export_id'])
            if not collection:
                continue

            kind = data['content_type']
            registry = registries.get(kind)
            content_object = registry.get(data['item_reference']) if registry is not None else None
            if not content_object:
                continue

            is_global = bool(data.get('is_global', False))
            day = None
            placement = {}
            if has_day_plan:
                day = self.days.get((data['collection_export_id'], data.get('day_index')))
                logged_ref = data.get('logged_visit_ref')
                placement = {
                    'span_end_index': data.get('span_end_index') if day else None,
                    'is_optional': bool(data.get('is_optional', False)),
                    'start_time': data.get('start_time'),
                    'end_time': data.get('end_time'),
                    'timezone': data.get('timezone'),
                    'logged_visit': self.visits.get(tuple(logged_ref)) if logged_ref else None,
                }
            self.placements[position] = CollectionItineraryItem.objects.create(
                collection=collection,
                content_type=ContentType.objects.get_for_model(type(content_object)),
                object_id=content_object.id,
                day=day,
                date=data.get('date') if not is_global else None,
                is_global=is_global,
                order=data['order'],
                **placement,
            )
            self.summary['itinerary_items'] += 1

    def _build_day_plans(self):
        """Schema 2 and older stored no days: build the plan once per trip from the records' dates."""
        col_datas = {c.get('export_id'): c for c in self.data.get('collections', [])}
        for export_id, collection in self.collections.items():
            if collection.type != 'trip':
                continue
            collection.refresh_from_db()
            day_count = col_datas.get(export_id, {}).get('day_count')
            if isinstance(day_count, int) and day_count >= 1:
                day_plan.build_days(collection, day_count)
            else:
                day_plan.convert_collection(collection)

    # ---- discussion

    def _comments(self):
        """
        Restore both threads. A comment keeps the name it was written under, but is linked to
        an account only when that account is the importer's own: a file must not be able to
        write as, or mention, somebody else.
        """
        importer_uuid = str(self.user.uuid)
        for col_data in self.data.get('collections', []):
            export_id = col_data.get('export_id')
            collection = self.collections.get(export_id)
            if collection is None:
                continue
            guest_links = self.guest_links.get(export_id) or {}
            created = {}
            for data in sorted(col_data.get('comments') or [], key=lambda c: c.get('export_id', 0)):
                body = (data.get('body') or '').strip()
                if not body:
                    continue
                author_user = self.user if str(data.get('author_user_uuid') or '') == importer_uuid else None
                author_guest = guest_links.get(data.get('author_guest_token')) if data.get('author_guest_token') else None
                comment = CollectionComment.objects.create(
                    collection=collection,
                    is_story=bool(data.get('is_story')),
                    parent=created.get(data.get('parent_export_id')),
                    day=self.days.get((export_id, data.get('day_index'))) if data.get('day_index') else None,
                    placement=self.placements.get(data.get('placement_ref')),
                    author_user=author_user,
                    author_guest=author_guest,
                    author_name=(data.get('author_name') or '')[:150],
                    body=body[:4000],
                    edited_at=parse_datetime(data['edited_at']) if data.get('edited_at') else None,
                )
                if data.get('created_at') and parse_datetime(data['created_at']):
                    CollectionComment.objects.filter(pk=comment.pk).update(created_at=parse_datetime(data['created_at']))
                if importer_uuid in (data.get('mention_uuids') or []):
                    comment.mentions.set([self.user])
                created[data.get('export_id')] = comment
