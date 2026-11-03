"""Building the JSON of a backup from the database.

One exporter serves both kinds of file. A whole-account backup carries everything the user
owns, including who their collections are shared with. A collection archive carries one
collection and what belongs to it, and leaves out sharing so the file can be passed around
without handing over access.
"""

from datetime import datetime

from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from adventures.models import Collection, CollectionItineraryDay, ContentImage, Lodging, Note, Checklist, Transportation
from adventures.utils.collection_type import BACKUP_SCHEMA
from adventures.services.day_plan.files import day_file_activities, day_file_images, day_file_trails

from . import serialization as ser
from .media import ArchiveMedia

COLLECTION_ARCHIVE = 'collection'


class BackupExporter:
    def __init__(self, user, collection=None):
        self.user = user
        self.collection = collection
        self.whole_account = collection is None

        if self.whole_account:
            self.collections = list(user.collection_set.all())
            self.locations = list(user.location_set.all())
            self.transportation = list(user.transportation_set.all())
            self.notes = list(user.note_set.all())
            self.checklists = list(user.checklist_set.all())
            self.lodging = list(user.lodging_set.all())
        else:
            self.collections = [collection]
            self.locations = list(
                collection.locations.all().select_related('city', 'region', 'country', 'category')
            )
            self.transportation = list(Transportation.objects.filter(collection=collection))
            self.notes = list(Note.objects.filter(collection=collection))
            self.checklists = list(Checklist.objects.filter(collection=collection))
            self.lodging = list(Lodging.objects.filter(collection=collection))

        self.collection_export_ids = {c.id: i for i, c in enumerate(self.collections)}
        self.export_ids = {
            'location': {obj.id: i for i, obj in enumerate(self.locations)},
            'transportation': {obj.id: i for i, obj in enumerate(self.transportation)},
            'note': {obj.id: i for i, obj in enumerate(self.notes)},
            'lodging': {obj.id: i for i, obj in enumerate(self.lodging)},
            'checklist': {obj.id: i for i, obj in enumerate(self.checklists)},
        }
        self.image_refs = {}
        self.visit_refs = {}
        self.placement_positions = {}

    # ---- the JSON

    def build(self):
        data = {
            'version': getattr(settings, 'ADVENTURELOG_RELEASE_VERSION', 'unknown'),
            'backup_schema': BACKUP_SCHEMA,
        }
        if self.whole_account:
            data['export_date'] = datetime.now().isoformat()
            data['user_email'] = self.user.email
            data['user_username'] = self.user.username
        else:
            data['archive_kind'] = COLLECTION_ARCHIVE
        data.update({
            'categories': [], 'collections': [], 'locations': [], 'transportation': [],
            'notes': [], 'checklists': [], 'lodging': [], 'visited_cities': [], 'visited_regions': [],
            'itinerary_days': [], 'itinerary_items': [], 'day_trails': [], 'day_activities': [],
            'day_images': [],
        })

        if self.whole_account:
            data['visited_cities'] = [{'city': v.city.id} for v in self.user.visitedcity_set.all()]
            data['visited_regions'] = [{'region': v.region.id} for v in self.user.visitedregion_set.all()]
        data['categories'] = self._categories()

        data['locations'] = [self._location(i, location) for i, location in enumerate(self.locations)]
        data['transportation'] = [self._transportation(i, obj) for i, obj in enumerate(self.transportation)]
        data['notes'] = [self._note(i, obj) for i, obj in enumerate(self.notes)]
        data['checklists'] = [self._checklist(i, obj) for i, obj in enumerate(self.checklists)]
        data['lodging'] = [self._lodging(i, obj) for i, obj in enumerate(self.lodging)]
        data['itinerary_items'] = self._itinerary_items()

        for index, collection in enumerate(self.collections):
            data['collections'].append(self._collection(index, collection))
            for day in collection.itinerary_days.all().order_by('index', 'date'):
                data['itinerary_days'].append({
                    'collection_export_id': index,
                    'index': day.index,
                    'date': ser.iso(day.date),
                    'name': day.name,
                    'description': day.description,
                })
            self._day_files(data, collection, index)

        self._primary_images(data)
        return data

    def _categories(self):
        if self.whole_account:
            categories = self.user.category_set.all()
        else:
            categories, seen = [], set()
            for location in self.locations:
                if location.category_id and location.category_id not in seen:
                    seen.add(location.category_id)
                    categories.append(location.category)
        return [
            {'name': c.name, 'display_name': c.display_name, 'icon': c.icon}
            for c in categories
        ]

    def _collection(self, index, collection):
        sharing = self.whole_account
        return {
            'export_id': index,
            'name': collection.name,
            'description': collection.description,
            'is_public': collection.is_public,
            'start_date': ser.iso(collection.start_date),
            'end_date': ser.iso(collection.end_date),
            'type': collection.type,
            'timezone': collection.timezone,
            'is_archived': collection.is_archived,
            'link': collection.link,
            'shared_with_user_ids': (
                [str(uuid) for uuid in collection.shared_with.values_list('uuid', flat=True)] if sharing else []
            ),
            'visibility': collection.visibility,
            'story_groups': {name: True for name in Collection.STORY_GROUPS if collection.story_group(name)},
            'comment_access': collection.comment_access,
            'comments': self._comments(collection),
            'members': (
                [
                    {'user_uuid': str(member.user.uuid), 'role': member.role}
                    for member in collection.members.select_related('user')
                ] if sharing else []
            ),
            'guest_links': (
                [
                    {
                        'token': link.token,
                        'role': link.role,
                        'label': link.label,
                        'expires_at': ser.iso(link.expires_at),
                        'revoked_at': ser.iso(link.revoked_at),
                    }
                    for link in collection.guest_links.all()
                ] if sharing else []
            ),
        }

    def _comments(self, collection):
        """Both threads, oldest first. A reply names its parent by position."""
        comments = list(
            collection.comments.select_related('author_user', 'author_guest', 'day').prefetch_related('mentions')
        )
        position = {comment.pk: i for i, comment in enumerate(comments)}
        return [
            {
                'export_id': i,
                'parent_export_id': position.get(comment.parent_id),
                'is_story': comment.is_story,
                'day_index': comment.day.index if comment.day_id else None,
                # Position of the placement in this file's itinerary_items.
                'placement_ref': self.placement_positions.get(comment.placement_id),
                'body': comment.body,
                'author_user_uuid': str(comment.author_user.uuid) if comment.author_user_id else None,
                # A guest token is a secret that opens the collection, so a shareable archive omits it.
                'author_guest_token': (
                    comment.author_guest.token if comment.author_guest_id and self.whole_account else None
                ),
                'author_name': comment.author_name,
                'mention_uuids': [str(user.uuid) for user in comment.mentions.all()],
                'created_at': comment.created_at.isoformat(),
                'edited_at': ser.iso(comment.edited_at),
            }
            for i, comment in enumerate(comments)
        ]

    def _remember_images(self, images, content_type, **where):
        for image_index, image in enumerate(images.all()):
            self.image_refs[image.id] = {
                'content_type': content_type,
                **where,
                'image_index': image_index,
                'immich_id': image.immich_id,
                'filename': ser.storage_basename(image.image.name) if image.image else None,
            }

    def _activity(self, activity):
        """The fields of an activity wherever it lives: on a visit, a day, or in Ideas."""
        start_lat, start_lng = ser.lat_lon_floats(activity.start_point)
        end_lat, end_lng = ser.lat_lon_floats(activity.end_point)
        return {
            'name': activity.name,
            'sport_type': activity.sport_type,
            'distance': ser.float_or_none(activity.distance),
            'moving_time': ser.seconds_or_none(activity.moving_time),
            'elapsed_time': ser.seconds_or_none(activity.elapsed_time),
            'rest_time': ser.seconds_or_none(activity.rest_time),
            'elevation_gain': ser.float_or_none(activity.elevation_gain),
            'elevation_loss': ser.float_or_none(activity.elevation_loss),
            'elev_high': ser.float_or_none(activity.elev_high),
            'elev_low': ser.float_or_none(activity.elev_low),
            'start_date': ser.iso(activity.start_date),
            'start_date_local': ser.iso(activity.start_date_local),
            'timezone': activity.timezone,
            'average_speed': ser.float_or_none(activity.average_speed),
            'max_speed': ser.float_or_none(activity.max_speed),
            'average_cadence': ser.float_or_none(activity.average_cadence),
            'calories': ser.float_or_none(activity.calories),
            'start_lat': start_lat,
            'start_lng': start_lng,
            'end_lat': end_lat,
            'end_lng': end_lng,
            'external_service_id': activity.external_service_id,
            'gpx_filename': ser.storage_basename(activity.gpx_file.name) if activity.gpx_file else None,
            'images': ser.serialize_images(activity.images),
        }

    def _visit_activity(self, activity):
        return {**self._activity(activity), 'trail_name': activity.trail.name if activity.trail else None}

    def _location(self, index, location):
        lat, lon = ser.lat_lon_strings(location.coordinates)
        price, price_currency = ser.money_fields(location.price)
        data = {
            'export_id': index,
            'name': location.name,
            'location': location.location,
            'tags': location.tags,
            'description': location.description,
            'rating': location.rating,
            'price': price,
            'price_currency': price_currency,
            'link': location.link,
            'is_public': location.is_public,
            'longitude': lon,
            'latitude': lat,
            'city': location.city_id,
            'region': location.region_id,
            'country': location.country_id,
            # Country PKs are not stable across installs; the ISO code is.
            'country_code': location.country.country_code if location.country_id else None,
            'category_name': location.category.name if location.category else None,
            'collection_export_ids': [
                self.collection_export_ids[collection_id]
                for collection_id in location.collections.values_list('id', flat=True)
                if collection_id in self.collection_export_ids
            ],
            'visits': [],
            'trails': [],
            'images': [],
            'attachments': [],
        }

        for visit_index, visit in enumerate(location.visits.all()):
            self.visit_refs[visit.id] = [index, visit_index]
            data['visits'].append({
                'export_id': visit_index,
                'start_date': ser.iso(visit.start_date),
                'end_date': ser.iso(visit.end_date),
                'timezone': visit.timezone,
                'notes': visit.notes,
                'activities': [self._visit_activity(a) for a in visit.activities.all()],
                'images': ser.serialize_images(visit.images),
                'attachments': ser.serialize_attachments(visit.attachments),
            })
            self._remember_images(
                visit.images, 'visit', location_export_id=index, visit_export_id=visit_index
            )

        data['trails'] = [ser.serialize_trail(trail) for trail in location.trails.all()]
        data['images'] = ser.serialize_images(location.images)
        self._remember_images(location.images, 'location', location_export_id=index)
        data['attachments'] = ser.serialize_attachments(location.attachments)
        return data

    def _collection_ref(self, obj):
        return self.collection_export_ids.get(obj.collection_id)

    def _transportation(self, index, transport):
        origin_lat, origin_lon = ser.lat_lon_strings(transport.origin)
        destination_lat, destination_lon = ser.lat_lon_strings(transport.destination)
        price, price_currency = ser.money_fields(transport.price)
        self._remember_images(transport.images, 'transportation', object_export_id=index)
        return {
            'export_id': index,
            'type': transport.type,
            'name': transport.name,
            'description': transport.description,
            'rating': transport.rating,
            'price': price,
            'price_currency': price_currency,
            'link': transport.link,
            'date': ser.iso(transport.date),
            'end_date': ser.iso(transport.end_date),
            'start_timezone': transport.start_timezone,
            'end_timezone': transport.end_timezone,
            'flight_number': transport.flight_number,
            'start_code': transport.start_code,
            'end_code': transport.end_code,
            'from_location': transport.from_location,
            'origin_latitude': origin_lat,
            'origin_longitude': origin_lon,
            'destination_latitude': destination_lat,
            'destination_longitude': destination_lon,
            'to_location': transport.to_location,
            'is_public': transport.is_public,
            'collection_export_id': self._collection_ref(transport),
            'images': ser.serialize_images(transport.images),
            'attachments': ser.serialize_attachments(transport.attachments),
        }

    def _note(self, index, note):
        self._remember_images(note.images, 'note', object_export_id=index)
        return {
            'export_id': index,
            'name': note.name,
            'content': note.content,
            'links': note.links,
            'date': ser.iso(note.date),
            'is_public': note.is_public,
            'is_private': note.is_private,
            'collection_export_id': self._collection_ref(note),
            'images': ser.serialize_images(note.images),
            'attachments': ser.serialize_attachments(note.attachments),
        }

    def _checklist(self, index, checklist):
        return {
            'export_id': index,
            'name': checklist.name,
            'date': ser.iso(checklist.date),
            'is_public': checklist.is_public,
            'collection_export_id': self._collection_ref(checklist),
            'items': [
                {'name': item.name, 'is_checked': item.is_checked, 'is_private': item.is_private}
                for item in checklist.checklistitem_set.all()
            ],
        }

    def _lodging(self, index, lodging):
        lat, lon = ser.lat_lon_strings(lodging.coordinates)
        price, price_currency = ser.money_fields(lodging.price)
        self._remember_images(lodging.images, 'lodging', object_export_id=index)
        return {
            'export_id': index,
            'name': lodging.name,
            'type': lodging.type,
            'description': lodging.description,
            'rating': lodging.rating,
            'link': lodging.link,
            'check_in': ser.iso(lodging.check_in),
            'check_out': ser.iso(lodging.check_out),
            'timezone': lodging.timezone,
            'reservation_number': lodging.reservation_number,
            'price': price,
            'price_currency': price_currency,
            'latitude': lat,
            'longitude': lon,
            'location': lodging.location,
            'is_public': lodging.is_public,
            'collection_export_id': self._collection_ref(lodging),
            'images': ser.serialize_images(lodging.images),
            'attachments': ser.serialize_attachments(lodging.attachments),
        }

    def _primary_images(self, data):
        for index, collection in enumerate(self.collections):
            primary = collection.primary_image
            if primary and primary.id in self.image_refs:
                data['collections'][index]['primary_image'] = self.image_refs[primary.id]

    def _itinerary_items(self):
        items = []
        for index, collection in enumerate(self.collections):
            for row in collection.itinerary_items.select_related('day', 'content_type'):
                kind = row.content_type.model
                reference = self.export_ids.get(kind, {}).get(row.object_id)
                if reference is None:
                    continue
                self.placement_positions[row.id] = len(items)
                items.append({
                    'collection_export_id': index,
                    'content_type': kind,
                    'item_reference': reference,
                    'date': ser.iso(row.date),
                    'is_global': row.is_global,
                    'order': row.order,
                    'day_index': row.day.index if row.day_id else None,
                    'span_end_index': row.span_end_index,
                    'is_optional': row.is_optional,
                    'start_time': ser.iso(row.start_time),
                    'end_time': ser.iso(row.end_time),
                    'timezone': row.timezone,
                    'logged_visit_ref': self.visit_refs.get(row.logged_visit_id),
                })
        return items

    def _day_files(self, data, collection, collection_export_id):
        """Trails, activities, and photos whose parent is a day or Ideas."""
        trail_keys = {}
        for trail in day_file_trails(collection):
            export_id = len(data['day_trails'])
            trail_keys[trail.id] = export_id
            data['day_trails'].append({
                'export_id': export_id,
                'collection_export_id': collection_export_id,
                'day_index': trail.day.index if trail.day_id else None,
                'name': trail.name,
                'link': trail.link,
                'wanderer_id': trail.wanderer_id,
                'wanderer_author_username': trail.wanderer_author_username,
                'wanderer_author_domain': trail.wanderer_author_domain,
                'span_end_index': trail.span_end_index,
                'images': ser.serialize_images(trail.images),
            })
        for activity in day_file_activities(collection):
            data['day_activities'].append({
                **self._activity(activity),
                'collection_export_id': collection_export_id,
                'day_index': activity.day.index if activity.day_id else None,
                'trail_export_id': trail_keys.get(activity.trail_id),
            })
        day_type = ContentType.objects.get_for_model(CollectionItineraryDay)
        collection_type = ContentType.objects.get_for_model(Collection)
        for image in day_file_images(collection).select_related('content_type'):
            if image.content_type_id not in (day_type.id, collection_type.id):
                continue
            entry = ser.serialize_images(ContentImage.objects.filter(pk=image.pk))
            if not entry:
                continue
            payload = entry[0]
            payload['collection_export_id'] = collection_export_id
            if image.content_type_id == day_type.id:
                day = CollectionItineraryDay.objects.filter(pk=image.object_id).first()
                payload['day_index'] = day.index if day else None
            else:
                payload['day_index'] = None
            data['day_images'].append(payload)

    # ---- the files

    def write_media(self, archive):
        """Add every stored file the JSON refers to."""
        media = ArchiveMedia(archive)
        for location in self.locations:
            for image in location.images.all():
                media.add_image(image)
            for visit in location.visits.all():
                for image in visit.images.all():
                    media.add_image(image)
            for attachment in location.attachments.all():
                media.add_attachment(attachment)
            for visit in location.visits.all():
                for attachment in visit.attachments.all():
                    media.add_attachment(attachment)
            for visit in location.visits.all():
                for activity in visit.activities.all():
                    media.add_gpx(activity)
                    for image in activity.images.all():
                        media.add_image(image)
            for trail in location.trails.all():
                for image in trail.images.all():
                    media.add_image(image)

        for collection in self.collections:
            for activity in day_file_activities(collection):
                media.add_gpx(activity)
            for image in day_file_images(collection):
                media.add_image(image)

        for record in (*self.transportation, *self.notes, *self.lodging):
            for image in record.images.all():
                media.add_image(image)
            for attachment in record.attachments.all():
                media.add_attachment(attachment)
