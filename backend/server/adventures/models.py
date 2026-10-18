import os
import uuid
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils.deconstruct import deconstructible
from adventures.utils.geo import has_coordinates, point_to_lat_lon
from adventures.managers import LocationManager
import threading
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django_resized import ResizedImageField
from djmoney.models.fields import MoneyField
from worldtravel.models import City, Country, Region, VisitedCity, VisitedRegion
from django.core.exceptions import ValidationError
from django.utils import timezone
from adventures.utils.timezones import TIMEZONES, validate_timezone
from adventures.utils.sports_types import SPORT_TYPE_CHOICES
from adventures.utils.get_is_visited import is_location_visited
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation

def background_geocode_and_assign(location_id: str):
    print(f"[Location Geocode Thread] Starting geocode for location {location_id}")
    try:
        location = Location.objects.get(id=location_id)
        if not has_coordinates(location.coordinates):
            return

        latitude, longitude = point_to_lat_lon(location.coordinates)
        from adventures.services.geocoding.reverse import reverse_geocode as reverse_geocode_service
        is_visited = location.is_visited_status()
        selection = reverse_geocode_service(latitude, longitude, location.user)
        result = selection.data

        if 'region_id' in result:
            region = Region.objects.filter(id=result['region_id']).first()
            if region:
                location.region = region
                if is_visited:
                    VisitedRegion.objects.get_or_create(user=location.user, region=region)

        if 'city_id' in result:
            city = City.objects.filter(id=result['city_id']).first()
            if city:
                location.city = city
                if is_visited:
                    VisitedCity.objects.get_or_create(user=location.user, city=city)

        if 'country_id' in result:
            country = Country.objects.filter(country_code=result['country_id']).first()
            if country:
                location.country = country

        # Save updated location info
        # Save updated location info, skip geocode threading
        location.save(update_fields=["region", "city", "country"], _skip_geocode=True)

    except Exception as e:
        # Optional: log or print the error
        print(f"[Location Geocode Thread] Error processing {location_id}: {e}")

def validate_file_extension(value):
    import os
    from django.core.exceptions import ValidationError
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp4', '.mov', '.avi', '.mkv', '.mp3', '.wav', '.flac', '.ogg', '.m4a', '.wma', '.aac', '.opus', '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.zst', '.lz4', '.lzma', '.lzo', '.z', '.tar.gz', '.tar.bz2', '.tar.xz', '.tar.zst', '.tar.lz4', '.tar.lzma', '.tar.lzo', '.tar.z', '.gpx', '.md']
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file extension.')

# Legacy support for old adventure types, not used in newer versions since custom categories are now used
ADVENTURE_TYPES = [
    ('general', 'General 🌍'),
    ('outdoor', 'Outdoor 🏞️'),
    ('lodging', 'Lodging 🛌'),
    ('dining', 'Dining 🍽️'),
    ('activity', 'Activity 🏄'),
    ('attraction', 'Attraction 🎢'),
    ('shopping', 'Shopping 🛍️'),
    ('nightlife', 'Nightlife 🌃'),
    ('event', 'Event 🎉'),
    ('transportation', 'Transportation 🚗'),
    ('culture', 'Culture 🎭'),
    ('water_sports', 'Water Sports 🚤'),
    ('hiking', 'Hiking 🥾'),
    ('wildlife', 'Wildlife 🦒'),
    ('historical_sites', 'Historical Sites 🏛️'),
    ('music_concerts', 'Music & Concerts 🎶'),
    ('fitness', 'Fitness 🏋️'),
    ('art_museums', 'Art & Museums 🎨'),
    ('festivals', 'Festivals 🎪'),
    ('spiritual_journeys', 'Spiritual Journeys 🧘‍♀️'),
    ('volunteer_work', 'Volunteer Work 🤝'),
    ('other', 'Other')
]

LODGING_TYPES = [
    ('hotel', 'Hotel'),
    ('hostel', 'Hostel'),
    ('resort', 'Resort'),
    ('bnb', 'Bed & Breakfast'),
    ('campground', 'Campground'),
    ('cabin', 'Cabin'),
    ('apartment', 'Apartment'),
    ('house', 'House'),
    ('villa', 'Villa'),
    ('motel', 'Motel'),
    ('other', 'Other')
]

TRANSPORTATION_TYPES = [
    ('car', 'Car'),
    ('plane', 'Plane'),
    ('train', 'Train'),
    ('bus', 'Bus'),
    ('boat', 'Boat'),
    ('bike', 'Bike'),
    ('walking', 'Walking'),
    ('other', 'Other')
]

# Assuming you have a default user ID you want to use
default_user = 1  # Replace with an actual user ID

User = get_user_model()

class Visit(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    location = models.ForeignKey('Location', on_delete=models.CASCADE, related_name='visits')
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in TIMEZONES], null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Generic relations for images and attachments
    images = GenericRelation('ContentImage', related_query_name='visit')
    attachments = GenericRelation('ContentAttachment', related_query_name='visit')

    def clean(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError('The start date must be before or equal to the end date.')

    def delete(self, *args, **kwargs):
        # Delete all associated images and attachments
        for image in self.images.all():
            image.delete()
        for attachment in self.attachments.all():
            attachment.delete()
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.location.name} - {self.start_date} to {self.end_date}"

class Location(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=default_user)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, blank=True, null=True)
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True, null=True)
    tags = ArrayField(models.CharField(max_length=100), blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)
    price = MoneyField(max_digits=12, decimal_places=2, default_currency='USD', null=True, blank=True)
    link = models.URLField(blank=True, null=True, max_length=2083)
    is_public = models.BooleanField(default=False)
    coordinates = gis_models.PointField(srid=4326, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, blank=True, null=True)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, blank=True, null=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, blank=True, null=True)
    collections = models.ManyToManyField('Collection', blank=True, related_name='locations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Generic relations for images and attachments
    images = GenericRelation('ContentImage', related_query_name='location')
    attachments = GenericRelation('ContentAttachment', related_query_name='location')

    objects = LocationManager()

    def is_visited_status(self):
        return is_location_visited(self)

    def clean(self, skip_shared_validation=False):
        """
        Validate model constraints.
        skip_shared_validation: Skip validation when called by shared users
        """
        # Skip validation if this is a shared user update
        if skip_shared_validation:
            return
            
        # Check collections after the instance is saved (in save method or separate validation)
        if self.pk:  # Only check if the instance has been saved
            for collection in self.collections.all():
                # Only enforce same-user constraint for non-shared collections
                if self.user != collection.user:
                    # Check if this is a shared collection scenario
                    # Allow if the location owner has access to the collection through sharing
                    if not collection.shared_with.filter(uuid=self.user.uuid).exists():
                        raise ValidationError(f'Locations must be associated with collections owned by the same user or shared collections. Collection owner: {collection.user.username} Location owner: {self.user.username}')
        
        if self.category:
            if self.user != self.category.user:
                raise ValidationError(f'Locations must be associated with categories owned by the same user. Category owner: {self.category.user.username} Location owner: {self.user.username}')
            
    def save(self, force_insert=False, force_update=False, using=None, update_fields=None, _skip_geocode=False, _skip_shared_validation=False):
        if force_insert and force_update:
            raise ValueError("Cannot force both insert and updating in model saving.")

        if not self.category:
            category, _ = Category.objects.get_or_create(
                user=self.user,
                name='general',
                defaults={'display_name': 'General', 'icon': '🌍'}
            )
            self.category = category

        result = super().save(force_insert, force_update, using, update_fields)

        # Validate collections after saving (since M2M relationships require saved instance)
        if self.pk:
            try:
                self.clean(skip_shared_validation=_skip_shared_validation)
            except ValidationError as e:
                # If validation fails, you might want to handle this differently
                # For now, we'll re-raise the error
                raise e

        # Skip threading when called from the geocode worker, and during tests.
        if _skip_geocode or getattr(settings, 'DISABLE_BACKGROUND_GEOCODE', False):
            return result

        if has_coordinates(self.coordinates):
            thread = threading.Thread(target=background_geocode_and_assign, args=(str(self.id),))
            thread.daemon = True  # Allows the thread to exit when the main program ends
            thread.start()

        return result

    def delete(self, *args, **kwargs):
        # Delete all associated images and attachments (handled by GenericRelation)
        for image in self.images.all():
            image.delete()
        for attachment in self.attachments.all():
            attachment.delete()
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name
    
class CollectionInvite(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, related_name='invites')
    invited_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collection_invites')
    role = models.CharField(max_length=10, default='editor', choices=[('editor', 'Editor'), ('viewer', 'Viewer')])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invite for {self.invited_user.username} to {self.collection.name}"
    
    def clean(self):
        if self.collection.user == self.invited_user:
            raise ValidationError("You cannot invite yourself to your own collection.")
        # dont allow if the user is already shared with the collection
        if self.invited_user in self.collection.shared_with.all():
            raise ValidationError("This user is already shared with the collection.")
    
    class Meta:
        verbose_name = "Collection Invite"
        unique_together = ('collection', 'invited_user')

def default_story_groups():
    return {}


def generate_share_secret():
    import secrets

    return secrets.token_urlsafe(24)


class Collection(models.Model):
    class Type(models.TextChoices):
        FOLDER = 'folder', 'Folder'
        TRIP = 'trip', 'Trip'

    class Visibility(models.TextChoices):
        PRIVATE = 'private', 'Private'
        UNLISTED = 'unlisted', 'Unlisted'
        PUBLIC = 'public', 'Public'

    # Story groups a public reader may see. Every group is off until the owner turns it on.
    STORY_GROUPS = (
        'place_details',
        'costs',
        'reservations',
        'attachments',
        'lodging_address',
        'coordinates',
        'gpx',
        'note_text',
        'checklist_text',
    )

    #id = models.AutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    type = models.CharField(max_length=10, choices=Type.choices, default=Type.FOLDER)
    timezone = models.CharField(max_length=50, default='UTC', validators=[validate_timezone])
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)
    # Who can read the published story. ``is_public`` mirrors ``visibility == public`` for old clients.
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PRIVATE)
    # Secret for an unlisted story link.
    share_secret = models.CharField(max_length=64, default=generate_share_secret, editable=False)
    story_groups = models.JSONField(default=default_story_groups, blank=True)
    # Members. Each one has a role in CollectionMember; a member with no row is an editor.
    shared_with = models.ManyToManyField(User, related_name='shared_with', blank=True)
    link = models.URLField(blank=True, null=True, max_length=2083)
    primary_image = models.ForeignKey(
        'ContentImage',
        on_delete=models.SET_NULL,
        related_name='primary_for_collections',
        null=True,
        blank=True,
    )

    def clean(self):
        # An unanchored day-based trip has neither date; any other trip needs both.
        if self.type == self.Type.TRIP and bool(self.start_date) != bool(self.end_date):
            raise ValidationError('A trip requires a start date and an end date.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._loaded_visibility = self.__dict__.get('visibility')

    def _sync_publicity(self):
        """
        Keep ``is_public`` a mirror of ``visibility``. A changed visibility wins;
        otherwise an old client that only set ``is_public`` moves visibility.
        """
        public = self.Visibility.PUBLIC
        if 'visibility' not in self.__dict__ or 'is_public' not in self.__dict__:
            return
        if self._state.adding:
            # A new row: an explicit visibility wins, else a legacy is_public=True publishes it.
            if self.visibility == self.Visibility.PRIVATE and self.is_public:
                self.visibility = public
            self.is_public = self.visibility == public
        elif self.visibility != self._loaded_visibility:
            self.is_public = self.visibility == public
        elif self.is_public != (self.visibility == public):
            if self.is_public:
                self.visibility = public
            elif self.visibility == public:
                self.visibility = self.Visibility.PRIVATE

    def save(self, *args, **kwargs):
        self._sync_publicity()
        update_fields = kwargs.get('update_fields')
        if update_fields is not None and ({'visibility', 'is_public'} & set(update_fields)):
            kwargs['update_fields'] = list(set(update_fields) | {'visibility', 'is_public'})
        super().save(*args, **kwargs)
        self._loaded_visibility = self.visibility

    def story_group(self, name):
        return bool((self.story_groups or {}).get(name))

    def delete(self, *args, **kwargs):
        from adventures.utils.day_files import purge_collection_day_files

        purge_collection_day_files(self)
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name


class CollectionMember(models.Model):
    """The role of a ``shared_with`` user. Editors change the plan; viewers read it."""

    class Role(models.TextChoices):
        EDITOR = 'editor', 'Editor'
        VIEWER = 'viewer', 'Viewer'

    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collection_memberships')
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.EDITOR)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['collection', 'user'], name='unique_collection_member'),
        ]

    def __str__(self):
        return f"{self.user} - {self.collection} ({self.role})"


def generate_guest_token():
    import secrets

    return secrets.token_urlsafe(32)


class CollectionGuestLink(models.Model):
    """A link that lets someone without an account read or edit the private plan."""

    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='guest_links')
    token = models.CharField(max_length=64, unique=True, default=generate_guest_token, editable=False)
    role = models.CharField(max_length=10, choices=CollectionMember.Role.choices, default=CollectionMember.Role.VIEWER)
    label = models.CharField(max_length=100, blank=True, default='')
    expires_at = models.DateTimeField(blank=True, null=True)
    revoked_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    @property
    def is_active(self):
        if self.revoked_at is not None:
            return False
        return self.expires_at is None or self.expires_at > timezone.now()

    def __str__(self):
        return f"Guest link for {self.collection} ({self.role})"

class Transportation(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=default_user)
    type = models.CharField(max_length=100, choices=TRANSPORTATION_TYPES)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)
    price = MoneyField(max_digits=12, decimal_places=2, default_currency='USD', null=True, blank=True)
    link = models.URLField(blank=True, null=True, max_length=2083)
    date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    start_timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in TIMEZONES], null=True, blank=True)
    end_timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in TIMEZONES], null=True, blank=True)
    flight_number = models.CharField(max_length=100, blank=True, null=True)
    from_location = models.CharField(max_length=200, blank=True, null=True)
    origin = gis_models.PointField(srid=4326, null=True, blank=True)
    destination = gis_models.PointField(srid=4326, null=True, blank=True)
    start_code = models.CharField(max_length=100, blank=True, null=True) # Could be airport code, station code, etc.
    end_code = models.CharField(max_length=100, blank=True, null=True)   # Could be airport code, station code, etc.
    to_location = models.CharField(max_length=200, blank=True, null=True)
    is_public = models.BooleanField(default=False)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Generic relations for images and attachments
    images = GenericRelation('ContentImage', related_query_name='transportation')
    attachments = GenericRelation('ContentAttachment', related_query_name='transportation')

    def clean(self):
        if self.date and self.end_date and self.date > self.end_date:
            raise ValidationError('The start date must be before the end date. Start date: ' + str(self.date) + ' End date: ' + str(self.end_date))
        
        if self.collection:
            if self.user != self.collection.user:
                raise ValidationError('Transportations must be associated with collections owned by the same user. Collection owner: ' + self.collection.user.username + ' Transportation owner: ' + self.user.username)

    def delete(self, *args, **kwargs):
        # Delete all associated images and attachments
        for image in self.images.all():
            image.delete()
        for attachment in self.attachments.all():
            attachment.delete()
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name

class Note(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=default_user)
    name = models.CharField(max_length=200)
    content = models.TextField(blank=True, null=True)
    links = ArrayField(models.URLField(), blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    is_public = models.BooleanField(default=False)
    # Hidden from the published story even when the note text group is on.
    is_private = models.BooleanField(default=False)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Generic relations for images and attachments
    images = GenericRelation('ContentImage', related_query_name='note')
    attachments = GenericRelation('ContentAttachment', related_query_name='note')

    def clean(self):
        if self.collection:
            if self.user != self.collection.user:
                raise ValidationError('Notes must be associated with collections owned by the same user. Collection owner: ' + self.collection.user.username + ' Note owner: ' + self.user.username)

    def delete(self, *args, **kwargs):
        # Delete all associated images and attachments
        for image in self.images.all():
            image.delete()
        for attachment in self.attachments.all():
            attachment.delete()
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name
    
class Checklist(models.Model):
    # id = models.AutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user)
    name = models.CharField(max_length=200)
    date = models.DateField(blank=True, null=True)
    is_public = models.BooleanField(default=False)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.collection:
            if self.user != self.collection.user:
                raise ValidationError('Checklists must be associated with collections owned by the same user. Collection owner: ' + self.collection.user.username + ' Checklist owner: ' + self.user.username)

    def __str__(self):
        return self.name

class ChecklistItem(models.Model):
    #id = models.AutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user)
    name = models.CharField(max_length=200)
    is_checked = models.BooleanField(default=False)
    # Hidden from the published story even when the checklist text group is on.
    is_private = models.BooleanField(default=False)
    checklist = models.ForeignKey('Checklist', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.user != self.checklist.user:
            raise ValidationError('Checklist items must be associated with checklists owned by the same user. Checklist owner: ' + self.checklist.user.username + ' Checklist item owner: ' + self.user.username)

    def __str__(self):
        return self.name

@deconstructible
class PathAndRename:
    def __init__(self, path):
        self.path = path

    def __call__(self, instance, filename):
        ext = filename.split('.')[-1]
        # Generate a new UUID for the filename
        filename = f"{uuid.uuid4()}.{ext}"
        return os.path.join(self.path, filename)

class ContentImage(models.Model):
    """Generic image model that can be attached to any content type"""

    class Source(models.TextChoices):
        UPLOAD = 'upload', 'Upload'
        GOOGLE = 'google', 'Google'
        WIKIPEDIA = 'wikipedia', 'Wikipedia'
        URL = 'url', 'URL'
        IMMICH = 'immich', 'Immich'

    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=default_user)
    image = ResizedImageField(
        force_format="WEBP",
        quality=75,
        keep_meta=True,
        upload_to=PathAndRename('images/'),
        blank=True,
        null=True,
    )
    immich_id = models.CharField(max_length=200, null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.UPLOAD,
    )
    source_url = models.URLField(max_length=2048, null=True, blank=True)
    coordinates = gis_models.PointField(srid=4326, null=True, blank=True)
    
    # Generic foreign key fields
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='content_images')
    object_id = models.UUIDField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = "Content Image"
        verbose_name_plural = "Content Images"
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def clean(self):
        # One of image or immich_id must be set, but not both
        has_image = bool(self.image and str(self.image).strip())
        has_immich_id = bool(self.immich_id and str(self.immich_id).strip())

        if has_image and has_immich_id:
            raise ValidationError("Cannot have both image file and Immich ID. Please provide only one.")
        if not has_image and not has_immich_id:
            raise ValidationError("Must provide either an image file or an Immich ID.")

    def save(self, *args, **kwargs):
        # Clean empty strings to None for proper database storage
        if not self.image:
            self.image = None
        if not self.immich_id or not str(self.immich_id).strip():
            self.immich_id = None
            
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Remove file from storage when deleting image
        if self.image:
            self.image.delete(save=False)
        super().delete(*args, **kwargs)

    def __str__(self):
        content_name = getattr(self.content_object, 'name', 'Unknown')
        return f"Image for {self.content_type.model}: {content_name}"

class ContentAttachment(models.Model):
    """Generic attachment model that can be attached to any content type"""
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=default_user)
    file = models.FileField(upload_to=PathAndRename('attachments/'), validators=[validate_file_extension])
    name = models.CharField(max_length=200, null=True, blank=True)
    
    # Generic foreign key fields
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='content_attachments')
    object_id = models.UUIDField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = "Content Attachment"
        verbose_name_plural = "Content Attachments"
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def delete(self, *args, **kwargs):
        if self.file:
            self.file.delete(save=False)
        super().delete(*args, **kwargs)

    def __str__(self):
        content_name = getattr(self.content_object, 'name', 'Unknown')
        return f"Attachment for {self.content_type.model}: {content_name}"

class Category(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user)
    name = models.CharField(max_length=200)
    display_name = models.CharField(max_length=200)
    icon = models.CharField(max_length=200, default='🌍')

    class Meta:
        verbose_name_plural = 'Categories'
        unique_together = ['name', 'user']

    def clean(self) -> None:
        self.name = self.name.lower().strip()

        return super().clean()
    
    
    def __str__(self):
        return self.name + ' - ' + self.display_name + ' - ' + self.icon
    
class Lodging(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=default_user)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=100, choices=LODGING_TYPES, default='other')
    description = models.TextField(blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)
    link = models.URLField(blank=True, null=True, max_length=2083)
    check_in = models.DateTimeField(blank=True, null=True)
    check_out = models.DateTimeField(blank=True, null=True)
    timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in TIMEZONES], null=True, blank=True)
    reservation_number = models.CharField(max_length=100, blank=True, null=True)
    price = MoneyField(max_digits=12, decimal_places=2, default_currency='USD', null=True, blank=True)
    coordinates = gis_models.PointField(srid=4326, null=True, blank=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    is_public = models.BooleanField(default=False)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Generic relations for images and attachments
    images = GenericRelation('ContentImage', related_query_name='lodging')
    attachments = GenericRelation('ContentAttachment', related_query_name='lodging')

    def clean(self):
        if self.check_in and self.check_out and self.check_in > self.check_out:
            raise ValidationError('The start date must be before the end date. Start date: ' + str(self.check_in) + ' End date: ' + str(self.check_out))
        
        if self.collection:
            if self.user != self.collection.user:
                raise ValidationError('Lodging must be associated with collections owned by the same user. Collection owner: ' + self.collection.user.username + ' Lodging owner: ' + self.user.username)

    def delete(self, *args, **kwargs):
        # Delete all associated images and attachments
        for image in self.images.all():
            image.delete()
        for attachment in self.attachments.all():
            attachment.delete()
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name
    
class Trail(models.Model):
    """
    Represents a trail associated with a user.
    Supports referencing either a Wanderer trail ID or an external link (e.g., AllTrails).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # A trail has one parent: a location, a trip day, or the collection while it sits in Ideas.
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='trails', blank=True, null=True)
    day = models.ForeignKey(
        'CollectionItineraryDay',
        on_delete=models.CASCADE,
        related_name='trails',
        blank=True,
        null=True,
    )
    collection = models.ForeignKey(
        'Collection',
        on_delete=models.CASCADE,
        related_name='idea_trails',
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=200)
    # Listed on each day from ``day.index`` through this index. The card is a link, not a GPX file.
    span_end_index = models.PositiveIntegerField(blank=True, null=True)

    # Either an external link (e.g., AllTrails, Trailforks) or a Wanderer ID
    link = models.URLField("External Trail Link", max_length=2083, blank=True, null=True)
    wanderer_id = models.CharField("Wanderer Trail ID", max_length=100, blank=True, null=True)
    wanderer_author_username = models.CharField(
        "Wanderer Author Username",
        max_length=255,
        blank=True,
        null=True,
    )
    wanderer_author_domain = models.CharField(
        "Wanderer Author Domain",
        max_length=255,
        blank=True,
        null=True,
        help_text="Author's Wanderer instance domain for /trail/view/@user@domain/id links.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    images = GenericRelation('ContentImage', related_query_name='trail')

    class Meta:
        verbose_name = "Trail"
        verbose_name_plural = "Trails"
        constraints = [
            models.CheckConstraint(
                name='trail_exactly_one_parent',
                check=(
                    Q(location__isnull=False, day__isnull=True, collection__isnull=True)
                    | Q(location__isnull=True, day__isnull=False, collection__isnull=True)
                    | Q(location__isnull=True, day__isnull=True, collection__isnull=False)
                ),
            ),
        ]

    def clean(self):
        parents = sum(parent is not None for parent in (self.location_id, self.day_id, self.collection_id))
        if parents != 1:
            raise ValidationError('A trail belongs to a location, a trip day, or Ideas.')
        if self.span_end_index is not None and self.day_id is None:
            raise ValidationError({'span_end_index': 'Only a trail on a day can span days.'})
        if self.day_id and self.span_end_index is not None and self.span_end_index < self.day.index:
            raise ValidationError({'span_end_index': 'A span cannot end before it starts.'})

        has_link = bool(self.link and str(self.link).strip())
        has_wanderer_id = bool(self.wanderer_id and str(self.wanderer_id).strip())

        if has_link and has_wanderer_id:
            raise ValidationError("Cannot have both a link and a Wanderer ID. Provide only one.")
        if not has_link and not has_wanderer_id:
            raise ValidationError("You must provide either a link or a Wanderer ID.")

    def save(self, *args, **kwargs):
        self.full_clean()  # Ensure clean() is called on save
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({'Wanderer' if self.wanderer_id else 'External'})"
    
class Activity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=default_user)
    # Exactly one parent: a visit (place log), a trip day, or the collection while it sits in Ideas.
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='activities', blank=True, null=True)
    day = models.ForeignKey(
        'CollectionItineraryDay',
        on_delete=models.CASCADE,
        related_name='activities',
        blank=True,
        null=True,
    )
    collection = models.ForeignKey(
        'Collection',
        on_delete=models.CASCADE,
        related_name='idea_activities',
        blank=True,
        null=True,
    )
    trail = models.ForeignKey(Trail, on_delete=models.CASCADE, related_name='activities', blank=True, null=True)
    # Set when Log visit has copied this day activity onto a visit. The day row stays.
    promoted_activity = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='promoted_from',
        blank=True,
        null=True,
    )

    # GPX File
    gpx_file = models.FileField(upload_to=PathAndRename('activities/'), validators=[validate_file_extension], blank=True, null=True)

    # Descriptive
    name = models.CharField(max_length=200)
    sport_type = models.CharField(max_length=100, choices=SPORT_TYPE_CHOICES, default='General')  # Optional detailed type

    # Time & Distance
    distance = models.FloatField(blank=True, null=True)  # in meters
    moving_time = models.DurationField(blank=True, null=True)
    elapsed_time = models.DurationField(blank=True, null=True)
    rest_time = models.DurationField(blank=True, null=True)

    # Elevation
    elevation_gain = models.FloatField(blank=True, null=True)  # in meters
    elevation_loss = models.FloatField(blank=True, null=True)  # estimated
    elev_high = models.FloatField(blank=True, null=True)
    elev_low = models.FloatField(blank=True, null=True)

    # Timing
    start_date = models.DateTimeField(blank=True, null=True)
    start_date_local = models.DateTimeField(blank=True, null=True)
    timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in TIMEZONES], blank=True, null=True)

    # Speed
    average_speed = models.FloatField(blank=True, null=True)  # in m/s
    max_speed = models.FloatField(blank=True, null=True)      # in m/s

    # Optional metrics
    average_cadence = models.FloatField(blank=True, null=True)
    calories = models.FloatField(blank=True, null=True)

    # Coordinates
    start_point = gis_models.PointField(srid=4326, null=True, blank=True)
    end_point = gis_models.PointField(srid=4326, null=True, blank=True)

    # Optional links
    external_service_id = models.CharField(max_length=100, blank=True, null=True)  # E.g., Strava ID

    images = GenericRelation('ContentImage', related_query_name='activity')

    def __str__(self):
        return f"{self.name} ({self.sport_type})"

    class Meta:
        verbose_name = "Activity"
        verbose_name_plural = "Activities"
        constraints = [
            models.CheckConstraint(
                name='activity_exactly_one_parent',
                check=(
                    Q(visit__isnull=False, day__isnull=True, collection__isnull=True)
                    | Q(visit__isnull=True, day__isnull=False, collection__isnull=True)
                    | Q(visit__isnull=True, day__isnull=True, collection__isnull=False)
                ),
            ),
        ]

class CollectionItineraryDay(models.Model):
    """
    A day in a collection's itinerary.

    Trips identify days by a 1-based contiguous ``index``; ``date`` then mirrors
    the projected date (anchor + index - 1) and is null without an anchor.
    """
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, related_name='itinerary_days')
    index = models.PositiveIntegerField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    name = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    images = GenericRelation('ContentImage', related_query_name='itinerary_day')
    
    class Meta:
        ordering = ['index', 'date']
        verbose_name = "Collection Itinerary Day"
        verbose_name_plural = "Collection Itinerary Days"
        constraints = [
            models.UniqueConstraint(
                fields=['collection', 'index'],
                name='unique_itinerary_day_index',
                condition=Q(index__isnull=False),
            ),
            models.UniqueConstraint(
                fields=['collection', 'date'],
                name='unique_itinerary_day_date_keyed',
                condition=Q(index__isnull=True) & Q(date__isnull=False),
            ),
        ]
    
    def __str__(self):
        label = f"Day {self.index}" if self.index else str(self.date)
        return f"{self.collection.name} - {label} - {self.name or 'Unnamed Day'}"


class CollectionItineraryItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    collection = models.ForeignKey(
        Collection,
        on_delete=models.CASCADE,
        related_name="itinerary_items"
    )

    # Generic reference to Visit, Transportation, Lodging, Note, etc
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    item = GenericForeignKey("content_type", "object_id")

    # Placement (planning concern, not content concern).
    # Day-based trips: a row sits on a day (``day`` set), in Ideas (no day, not
    # global), or trip-wide (``is_global``). ``date`` mirrors the day's projected
    # date. Date-keyed trips: a row has a ``date`` or is global.
    day = models.ForeignKey(
        CollectionItineraryDay,
        on_delete=models.SET_NULL,
        related_name="items",
        blank=True,
        null=True,
    )
    date = models.DateField(blank=True, null=True)
    is_global = models.BooleanField(default=False, help_text="Applies to the whole trip (no specific date)")
    order = models.PositiveIntegerField(help_text="Manual order within a day")

    # Lodging and transportation can cover several days; the row lives on its
    # start day and lists on every day through span_end_index.
    span_end_index = models.PositiveIntegerField(blank=True, null=True)
    is_optional = models.BooleanField(default=False)
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    timezone = models.CharField(max_length=50, blank=True, null=True, validators=[validate_timezone])
    logged_visit = models.ForeignKey(
        Visit,
        on_delete=models.SET_NULL,
        related_name="itinerary_placements",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "order"]
        constraints = [
            # Date-keyed trips: unique order per date
            models.UniqueConstraint(
                fields=["collection", "date", "order"],
                name="unique_order_per_collection_day",
                condition=Q(is_global=False) & Q(date__isnull=False) & Q(day__isnull=True),
            ),
            # Day-based trips: unique order per day
            models.UniqueConstraint(
                fields=["collection", "day", "order"],
                name="unique_order_per_itinerary_day",
                condition=Q(day__isnull=False),
            ),
            # Ideas: unique order among unplaced rows
            models.UniqueConstraint(
                fields=["collection", "order"],
                name="unique_order_per_collection_ideas",
                condition=Q(day__isnull=True) & Q(is_global=False) & Q(date__isnull=True),
            ),
            # Ensure unique order within the global group for a collection
            models.UniqueConstraint(
                fields=["collection", "order"],
                name="unique_order_per_collection_global",
                condition=Q(is_global=True),
            ),
        ]

    def __str__(self):
        if self.is_global:
            scope = "GLOBAL"
        elif self.day_id:
            scope = f"Day {self.day.index}"
        elif self.date:
            scope = str(self.date)
        else:
            scope = "IDEAS"
        return f"{self.collection.name} - {self.content_type.model} - {scope} ({self.order})"

    def clean(self):
        if self.is_global and (self.date is not None or self.day_id is not None):
            raise ValidationError({
                "is_global": "Global items must not have a date.",
                "date": "Provide either a date or set is_global, not both.",
            })
        if self.span_end_index is not None:
            if self.day_id is None:
                raise ValidationError({"span_end_index": "Only placements on a day can span days."})
            if self.span_end_index < self.day.index:
                raise ValidationError({"span_end_index": "A span cannot end before it starts."})
    
    @property
    def start_datetime(self):
        obj = self.item

        for field in ("start_date", "check_in", "date"):
            if hasattr(obj, field):
                value = getattr(obj, field)
                if value:
                    return value

        return None

    @property
    def end_datetime(self):
        obj = self.item

        for field in ("end_date", "check_out"):
            if hasattr(obj, field):
                value = getattr(obj, field)
                if value:
                    return value

        return None
