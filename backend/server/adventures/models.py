import os
import uuid
from django.db import models
from django.utils.deconstruct import deconstructible
from adventures.managers import LocationManager
import threading
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django_resized import ResizedImageField
from djmoney.models.fields import MoneyField
from worldtravel.models import City, Country, Region
from django.core.exceptions import ValidationError
from django.utils import timezone
from adventures.utils.timezones import TIMEZONES
from adventures.utils.sports_types import SPORT_TYPE_CHOICES
from adventures.utils.get_is_visited import is_location_visited
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation
from adventures.utils.model_mixins import MediaDeletionMixin, SoftDeletableMixin

from adventures.utils.geocoding_tasks import background_geocode

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
    ('cab', 'Cab'),
    ('vtc', 'VTC'),
    ('other', 'Other')
]

# Assuming you have a default user ID you want to use
default_user = 1  # Replace with an actual user ID

User = get_user_model()


class TransportationType(models.Model):
    """Admin-managed transportation types with icons."""
    key = models.CharField(max_length=50, unique=True, help_text="Unique identifier (e.g., 'plane', 'train')")
    name = models.CharField(max_length=100, help_text="Display name (e.g., 'Plane', 'Train')")
    icon = models.CharField(max_length=10, help_text="Emoji icon (e.g., '✈️', '🚆')")
    display_order = models.IntegerField(default=0, help_text="Order in dropdown lists")
    is_active = models.BooleanField(default=True, help_text="Whether this type is available for selection")

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = "Transportation Type"
        verbose_name_plural = "Transportation Types"

    def __str__(self):
        return f"{self.icon} {self.name}"


class LodgingType(models.Model):
    """Admin-managed lodging types with icons."""
    key = models.CharField(max_length=50, unique=True, help_text="Unique identifier (e.g., 'hotel', 'hostel')")
    name = models.CharField(max_length=100, help_text="Display name (e.g., 'Hotel', 'Hostel')")
    icon = models.CharField(max_length=10, help_text="Emoji icon (e.g., '🏨', '🛏️')")
    display_order = models.IntegerField(default=0, help_text="Order in dropdown lists")
    is_active = models.BooleanField(default=True, help_text="Whether this type is available for selection")

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = "Lodging Type"
        verbose_name_plural = "Lodging Types"

    def __str__(self):
        return f"{self.icon} {self.name}"


class AdventureType(models.Model):
    """Admin-managed adventure/location category types with icons."""
    key = models.CharField(max_length=50, unique=True, help_text="Unique identifier (e.g., 'hiking', 'dining')")
    name = models.CharField(max_length=100, help_text="Display name (e.g., 'Hiking', 'Dining')")
    icon = models.CharField(max_length=10, help_text="Emoji icon (e.g., '🥾', '🍽️')")
    display_order = models.IntegerField(default=0, help_text="Order in dropdown lists")
    is_active = models.BooleanField(default=True, help_text="Whether this type is available for selection")

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = "Adventure Type"
        verbose_name_plural = "Adventure Types"

    def __str__(self):
        return f"{self.icon} {self.name}"


class ActivityType(models.Model):
    """Admin-managed activity/sport types with icons and colors."""
    key = models.CharField(max_length=50, unique=True, help_text="Unique identifier (e.g., 'Run', 'Hike')")
    name = models.CharField(max_length=100, help_text="Display name (e.g., 'Run', 'Hike')")
    icon = models.CharField(max_length=10, help_text="Emoji icon (e.g., '🏃', '🥾')")
    color = models.CharField(max_length=20, default='#6B7280', help_text="Color code (e.g., '#F59E0B')")
    display_order = models.IntegerField(default=0, help_text="Order in dropdown lists")
    is_active = models.BooleanField(default=True, help_text="Whether this type is available for selection")

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = "Activity Type"
        verbose_name_plural = "Activity Types"

    def __str__(self):
        return f"{self.icon} {self.name}"

class Visit(MediaDeletionMixin, models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    # A visit must be associated with exactly one of: Location, Transportation, or Lodging
    location = models.ForeignKey('Location', on_delete=models.CASCADE, related_name='visits', null=True, blank=True)
    transportation = models.ForeignKey('Transportation', on_delete=models.CASCADE, related_name='visits', null=True, blank=True)
    lodging = models.ForeignKey('Lodging', on_delete=models.CASCADE, related_name='visits', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='visits')
    # Optional: collection this visit was created from (for itinerary planning)
    collection = models.ForeignKey('Collection', on_delete=models.SET_NULL, null=True, blank=True, related_name='planned_visits')
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in TIMEZONES], null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)  # User's rating for this visit
    # Price tracking for this visit
    total_price = MoneyField(max_digits=12, decimal_places=2, default_currency='USD', null=True, blank=True)
    number_of_people = models.PositiveIntegerField(null=True, blank=True)  # Number of people this price covers
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Generic relations for images and attachments
    images = GenericRelation('ContentImage', related_query_name='visit')
    attachments = GenericRelation('ContentAttachment', related_query_name='visit')

    def clean(self):
        # Validation: exactly one parent must be set
        parent_count = sum([
            self.location is not None,
            self.transportation is not None,
            self.lodging is not None
        ])
        if parent_count != 1:
            raise ValidationError('Visit must be associated with exactly one of: Location, Transportation, or Lodging.')

        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError('The start date must be before or equal to the end date.')

    def __str__(self):
        try:
            if self.location_id and self.location:
                parent_name = self.location.name
            elif self.transportation_id and self.transportation:
                parent_name = self.transportation.name
            elif self.lodging_id and self.lodging:
                parent_name = self.lodging.name
            else:
                parent_name = "Unknown"
        except (Location.DoesNotExist, Transportation.DoesNotExist, Lodging.DoesNotExist):
            parent_name = "Deleted"
        return f"{parent_name} - {self.start_date} to {self.end_date}"

class Location(MediaDeletionMixin, models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=default_user)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, blank=True, null=True)
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True, null=True)
    tags = ArrayField(models.CharField(max_length=100), blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)  # Deprecated: use average_rating from visits
    average_rating = models.FloatField(blank=True, null=True)  # Cached average from visit ratings
    price = MoneyField(max_digits=12, decimal_places=2, default_currency='USD', null=True, blank=True)
    link = models.URLField(blank=True, null=True, max_length=2083)
    is_public = models.BooleanField(default=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
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
                if collection.is_public and not self.is_public:
                    raise ValidationError(f'Locations associated with a public collection must be public. Collection: {collection.name} Location: {self.name}')
                
                # Only enforce same-user constraint for non-shared collections
                if self.user != collection.user:
                    # In collaborative mode, allow adding public locations to any collection
                    from django.conf import settings
                    is_collaborative = getattr(settings, 'COLLABORATIVE_MODE', False)
                    if is_collaborative and self.is_public:
                        continue  # Allow public locations in collaborative mode

                    # Check if this is a shared collection scenario
                    # Allow if the location owner has access to the collection through sharing
                    if not collection.shared_with.filter(uuid=self.user.uuid).exists():
                        raise ValidationError(f'Locations must be associated with collections owned by the same user or shared collections. Collection owner: {collection.user.username} Location owner: {self.user.username}')
        
        if self.category:
            # In collaborative mode, skip category owner validation for public locations
            # This allows any authenticated user to use any category on public content
            from django.conf import settings
            is_collaborative = getattr(settings, 'COLLABORATIVE_MODE', False)
            if not is_collaborative and self.user != self.category.user:
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

        # Skip validation when only updating computed fields like average_rating
        skip_validation = update_fields and set(update_fields) <= {'average_rating', 'updated_at'}

        # Validate collections after saving (since M2M relationships require saved instance)
        if self.pk and not skip_validation:
            try:
                self.clean(skip_shared_validation=_skip_shared_validation)
            except ValidationError as e:
                # If validation fails, you might want to handle this differently
                # For now, we'll re-raise the error
                raise e

        # ⛔ Skip threading if called from geocode background thread
        if _skip_geocode:
            return result

        if self.latitude and self.longitude:
            thread = threading.Thread(target=background_geocode, args=(Location, str(self.id)))
            thread.daemon = True
            thread.start()

        return result

    def __str__(self):
        return self.name

class CollectionInvite(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, related_name='invites')
    invited_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collection_invites')
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

class Collection(models.Model):
    #id = models.AutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)
    shared_with = models.ManyToManyField(User, related_name='shared_with', blank=True)
    link = models.URLField(blank=True, null=True, max_length=2083)
    primary_image = models.ForeignKey(
        'ContentImage',
        on_delete=models.SET_NULL,
        related_name='primary_for_collections',
        null=True,
        blank=True,
    )
    adventure_type = models.ForeignKey(
        'AdventureType',
        on_delete=models.SET_NULL,
        related_name='collections',
        null=True,
        blank=True,
        help_text="Category/type of this collection"
    )

    # if connected locations are private and collection is public, raise an error
    def clean(self):
        if self.is_public and self.pk:  # Only check if the instance has a primary key
            # Updated to use the new related_name 'locations'
            for location in self.locations.all():
                if not location.is_public:
                    raise ValidationError(f'Public collections cannot be associated with private locations. Collection: {self.name} Location: {location.name}')

    def __str__(self):
        return self.name
    
class Transportation(MediaDeletionMixin, models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=default_user)
    type = models.CharField(max_length=100, choices=TRANSPORTATION_TYPES)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)  # Deprecated: use average_rating from visits
    average_rating = models.FloatField(blank=True, null=True)  # Cached average from visit ratings
    price = MoneyField(max_digits=12, decimal_places=2, default_currency='USD', null=True, blank=True)
    link = models.URLField(blank=True, null=True, max_length=2083)
    # Date fields removed - now handled by Visit model
    flight_number = models.CharField(max_length=100, blank=True, null=True)
    from_location = models.CharField(max_length=200, blank=True, null=True)
    origin_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    origin_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    origin_country = models.ForeignKey(Country, on_delete=models.SET_NULL, blank=True, null=True, related_name='transportation_origins')
    destination_country = models.ForeignKey(Country, on_delete=models.SET_NULL, blank=True, null=True, related_name='transportation_destinations')
    start_code = models.CharField(max_length=100, blank=True, null=True) # Could be airport code, station code, etc.
    end_code = models.CharField(max_length=100, blank=True, null=True)   # Could be airport code, station code, etc.
    to_location = models.CharField(max_length=200, blank=True, null=True)
    tags = ArrayField(models.CharField(max_length=100), blank=True, null=True)
    is_public = models.BooleanField(default=True)
    collections = models.ManyToManyField('Collection', blank=True, related_name='transportations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Generic relations for images and attachments
    images = GenericRelation('ContentImage', related_query_name='transportation')
    attachments = GenericRelation('ContentAttachment', related_query_name='transportation')

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None, _skip_geocode=False):
        if force_insert and force_update:
            raise ValueError("Cannot force both insert and updating in model saving.")

        result = super().save(force_insert, force_update, using, update_fields)

        # Skip threading if called from geocode background thread
        if _skip_geocode:
            return result

        # Trigger geocoding if origin or destination coordinates are set
        if (self.origin_latitude and self.origin_longitude) or (self.destination_latitude and self.destination_longitude):
            thread = threading.Thread(target=background_geocode, args=(Transportation, str(self.id)))
            thread.daemon = True
            thread.start()

        return result

    def __str__(self):
        return self.name

class Note(MediaDeletionMixin, models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=default_user)
    name = models.CharField(max_length=200)
    content = models.TextField(blank=True, null=True)
    links = ArrayField(models.URLField(), blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    is_public = models.BooleanField(default=False)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Generic relations for images and attachments
    images = GenericRelation('ContentImage', related_query_name='note')
    attachments = GenericRelation('ContentAttachment', related_query_name='note')

    def clean(self):
        if self.collection:
            if self.collection.is_public and not self.is_public:
                raise ValidationError('Notes associated with a public collection must be public. Collection: ' + self.collection.name + ' Note: ' + self.name)
            if self.user != self.collection.user:
                raise ValidationError('Notes must be associated with collections owned by the same user. Collection owner: ' + self.collection.user.username + ' Note owner: ' + self.user.username)

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
            if self.collection.is_public and not self.is_public:
                raise ValidationError('Checklists associated with a public collection must be public. Collection: ' + self.collection.name + ' Checklist: ' + self.name)
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
    checklist = models.ForeignKey('Checklist', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.checklist.is_public and not self.checklist.is_public:
            raise ValidationError('Checklist items associated with a public checklist must be public. Checklist: ' + self.checklist.name + ' Checklist item: ' + self.name)
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

class ContentImage(SoftDeletableMixin, models.Model):
    """Generic image model that can be attached to any content type"""
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=default_user)
    image = ResizedImageField(
        force_format="WEBP",
        quality=75,
        upload_to=PathAndRename('images/'),
        blank=True,
        null=True,
    )
    immich_id = models.CharField(max_length=200, null=True, blank=True)
    is_primary = models.BooleanField(default=False)

    # Soft-delete fields for collaborative mode revert
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='deleted_images'
    )

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

    def _get_file_field(self):
        return self.image

    def __str__(self):
        content_name = getattr(self.content_object, 'name', 'Unknown')
        return f"Image for {self.content_type.model}: {content_name}"

class ContentAttachment(SoftDeletableMixin, models.Model):
    """Generic attachment model that can be attached to any content type"""
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=default_user)
    file = models.FileField(upload_to=PathAndRename('attachments/'), validators=[validate_file_extension])
    name = models.CharField(max_length=200, null=True, blank=True)

    # Soft-delete fields for collaborative mode revert
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='deleted_attachments'
    )

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

    def _get_file_field(self):
        return self.file

    def __str__(self):
        content_name = getattr(self.content_object, 'name', 'Unknown')
        return f"Attachment for {self.content_type.model}: {content_name}"

class Category(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user, null=True, blank=True)
    name = models.CharField(max_length=200)
    display_name = models.CharField(max_length=200)
    icon = models.CharField(max_length=200, default='🌍')
    is_global = models.BooleanField(default=False)  # True for collaborative mode categories

    class Meta:
        verbose_name_plural = 'Categories'
        unique_together = ['name', 'user']

    def clean(self) -> None:
        self.name = self.name.lower().strip()

        return super().clean()


    def __str__(self):
        return self.name + ' - ' + self.display_name + ' - ' + self.icon
    
class Lodging(MediaDeletionMixin, models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=default_user)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=100, choices=LODGING_TYPES, default='other')
    description = models.TextField(blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)  # Deprecated: use average_rating from visits
    average_rating = models.FloatField(blank=True, null=True)  # Cached average from visit ratings
    link = models.URLField(blank=True, null=True, max_length=2083)
    # Date fields removed - now handled by Visit model
    reservation_number = models.CharField(max_length=100, blank=True, null=True)
    price = MoneyField(max_digits=12, decimal_places=2, default_currency='USD', null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, blank=True, null=True, related_name='lodgings')
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, blank=True, null=True, related_name='lodgings')
    city = models.ForeignKey(City, on_delete=models.SET_NULL, blank=True, null=True, related_name='lodgings')
    tags = ArrayField(models.CharField(max_length=100), blank=True, null=True)
    is_public = models.BooleanField(default=True)
    collections = models.ManyToManyField('Collection', blank=True, related_name='lodgings')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Generic relations for images and attachments
    images = GenericRelation('ContentImage', related_query_name='lodging')
    attachments = GenericRelation('ContentAttachment', related_query_name='lodging')

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None, _skip_geocode=False):
        if force_insert and force_update:
            raise ValueError("Cannot force both insert and updating in model saving.")

        result = super().save(force_insert, force_update, using, update_fields)

        # Skip threading if called from geocode background thread
        if _skip_geocode:
            return result

        if self.latitude and self.longitude:
            thread = threading.Thread(target=background_geocode, args=(Lodging, str(self.id)))
            thread.daemon = True
            thread.start()

        return result

    def __str__(self):
        return self.name

class Trail(models.Model):
    """
    Represents a trail associated with a user.
    Supports referencing either a Wanderer trail ID or an external link (e.g., AllTrails).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='trails')
    name = models.CharField(max_length=200)

    # Either an external link (e.g., AllTrails, Trailforks) or a Wanderer ID
    link = models.URLField("External Trail Link", max_length=2083, blank=True, null=True)
    wanderer_id = models.CharField("Wanderer Trail ID", max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Trail"
        verbose_name_plural = "Trails"

    def clean(self):
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
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='activities')
    trail = models.ForeignKey(Trail, on_delete=models.CASCADE, related_name='activities', blank=True, null=True)

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
    start_lat = models.FloatField(blank=True, null=True)
    start_lng = models.FloatField(blank=True, null=True)
    end_lat = models.FloatField(blank=True, null=True)
    end_lng = models.FloatField(blank=True, null=True)

    # Optional links
    external_service_id = models.CharField(max_length=100, blank=True, null=True)  # E.g., Strava ID

    def __str__(self):
        return f"{self.name} ({self.sport_type})"

    class Meta:
        verbose_name = "Activity"
        verbose_name_plural = "Activities"

class CollectionItineraryDay(models.Model):
    """Metadata for a specific day in a collection's itinerary"""
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, related_name='itinerary_days')
    date = models.DateField()
    name = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['collection', 'date']]
        ordering = ['date']
        verbose_name = "Collection Itinerary Day"
        verbose_name_plural = "Collection Itinerary Days"
    
    def __str__(self):
        return f"{
            self.collection.name} - {self.date} - {self.name or 'Unnamed Day'}"


class CollectionTemplate(models.Model):
    """Reusable template for creating new collections with pre-defined structure"""
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    template_data = models.JSONField(default=dict)
    # Structure: {notes: [...], checklists: [...], transportations: [...], lodgings: [...]}
    is_public = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collection_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({'Public' if self.is_public else 'Private'})"


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

    # Placement (planning concern, not content concern)
    # Either a specific date or marked as trip-wide (global). Exactly one of these applies.
    date = models.DateField(blank=True, null=True)
    is_global = models.BooleanField(default=False, help_text="Applies to the whole trip (no specific date)")
    order = models.PositiveIntegerField(help_text="Manual order within a day")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "order"]
        constraints = [
            # Ensure unique order per day for dated items
            models.UniqueConstraint(
                fields=["collection", "date", "order"],
                name="unique_order_per_collection_day",
                condition=Q(is_global=False) & Q(date__isnull=False),
            ),
            # Ensure unique order within the global group for a collection
            models.UniqueConstraint(
                fields=["collection", "order"],
                name="unique_order_per_collection_global",
                condition=Q(is_global=True),
            ),
        ]

    def __str__(self):
        scope = "GLOBAL" if self.is_global else str(self.date)
        return f"{self.collection.name} - {self.content_type.model} - {scope} ({self.order})"

    def clean(self):
        # Enforce XOR between date and is_global
        if self.is_global and self.date is not None:
            raise ValidationError({
                "is_global": "Global items must not have a date.",
                "date": "Provide either a date or set is_global, not both.",
            })
        if (not self.is_global) and self.date is None:
            raise ValidationError({
                "date": "Dated items must include a date. To create a trip-wide item, set is_global=true.",
            })
    
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


class AuditLog(models.Model):
    """Tracks all modifications to content in collaborative mode."""

    ACTION_CHOICES = [
        ('create', 'Created'),
        ('update', 'Updated'),
        ('delete', 'Deleted'),
    ]

    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    object_repr = models.CharField(max_length=200)  # e.g., "Location: Paris Trip"
    changes = models.JSONField(default=dict)  # {"field": {"old": x, "new": y}}
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['user', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.action} {self.object_repr} by {self.user}"
