from django.core.exceptions import ValidationError
import os
import uuid
from django.db import models
from django.utils.deconstruct import deconstructible
from adventures.managers import LocationManager
import threading
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.forms import ValidationError
from django_resized import ResizedImageField
from worldtravel.models import City, Country, Region, VisitedCity, VisitedRegion
from django.core.exceptions import ValidationError
from django.utils import timezone
from adventures.utils.timezones import TIMEZONES

def background_geocode_and_assign(location_id: str):
    print(f"[Location Geocode Thread] Starting geocode for location {location_id}")
    try:
        location = Location.objects.get(id=location_id)
        if not (location.latitude and location.longitude):
            return
        
        from adventures.geocoding import reverse_geocode  # or wherever you defined it
        is_visited = location.is_visited_status()
        result = reverse_geocode(location.latitude, location.longitude, location.user)

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

    def clean(self):
        if self.start_date > self.end_date:
            raise ValidationError('The start date must be before or equal to the end date.')

    def __str__(self):
        return f"{self.location.name} - {self.start_date} to {self.end_date}"

class Location(models.Model):
    #id = models.AutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user)

    category = models.ForeignKey('Category', on_delete=models.SET_NULL, blank=True, null=True)
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True, null=True)
    tags = ArrayField(models.CharField(
        max_length=100), blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)
    link = models.URLField(blank=True, null=True, max_length=2083)
    is_public = models.BooleanField(default=False)

    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    city = models.ForeignKey(City, on_delete=models.SET_NULL, blank=True, null=True)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, blank=True, null=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, blank=True, null=True)

    # Changed from ForeignKey to ManyToManyField
    collections = models.ManyToManyField('Collection', blank=True, related_name='locations')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = LocationManager()

    def is_visited_status(self):
        current_date = timezone.now().date()
        for visit in self.visits.all():
            start_date = visit.start_date.date() if isinstance(visit.start_date, timezone.datetime) else visit.start_date
            end_date = visit.end_date.date() if isinstance(visit.end_date, timezone.datetime) else visit.end_date
            if start_date and end_date and (start_date <= current_date):
                return True
            elif start_date and not end_date and (start_date <= current_date):
                return True
        return False

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

        # ⛔ Skip threading if called from geocode background thread
        if _skip_geocode:
            return result

        if self.latitude and self.longitude:
            thread = threading.Thread(target=background_geocode_and_assign, args=(str(self.id),))
            thread.daemon = True  # Allows the thread to exit when the main program ends
            thread.start()

        return result

    def delete(self, *args, **kwargs):
        # Delete all associated AdventureImages first to trigger their filesystem cleanup
        for image in self.images.all():
            image.delete()
        # Delete all associated Attachment files first to trigger their filesystem cleanup
        for attachment in self.attachments.all():
            attachment.delete()
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name

class Collection(models.Model):
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
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)
    shared_with = models.ManyToManyField(User, related_name='shared_with', blank=True)
    link = models.URLField(blank=True, null=True, max_length=2083)

    # if connected locations are private and collection is public, raise an error
    def clean(self):
        if self.is_public and self.pk:  # Only check if the instance has a primary key
            # Updated to use the new related_name 'locations'
            for location in self.locations.all():
                if not location.is_public:
                    raise ValidationError(f'Public collections cannot be associated with private locations. Collection: {self.name} Location: {location.name}')

    def __str__(self):
        return self.name
    
class Transportation(models.Model):
    #id = models.AutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user)
    type = models.CharField(max_length=100, choices=TRANSPORTATION_TYPES)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    start_timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in TIMEZONES], null=True, blank=True)
    end_timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in TIMEZONES], null=True, blank=True)
    flight_number = models.CharField(max_length=100, blank=True, null=True)
    from_location = models.CharField(max_length=200, blank=True, null=True)
    origin_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    origin_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    to_location = models.CharField(max_length=200, blank=True, null=True)
    is_public = models.BooleanField(default=False)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        print(self.date)
        if self.date and self.end_date and self.date > self.end_date:
            raise ValidationError('The start date must be before the end date. Start date: ' + str(self.date) + ' End date: ' + str(self.end_date))
        
        if self.collection:
            if self.collection.is_public and not self.is_public:
                raise ValidationError('Transportations associated with a public collection must be public. Collection: ' + self.collection.name + ' Transportation: ' + self.name)
            if self.user != self.collection.user:
                raise ValidationError('Transportations must be associated with collections owned by the same user. Collection owner: ' + self.collection.user.username + ' Transportation owner: ' + self.user.username)

    def __str__(self):
        return self.name

class Note(models.Model):
    #id = models.AutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user)
    name = models.CharField(max_length=200)
    content = models.TextField(blank=True, null=True)
    links = ArrayField(models.URLField(), blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    is_public = models.BooleanField(default=False)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.collection:
            if self.collection.is_public and not self.is_public:
                raise ValidationError('Notes associated with a public collection must be public. Collection: ' + self.collection.name + ' Transportation: ' + self.name)
            if self.user != self.collection.user:
                raise ValidationError('Notes must be associated with collections owned by the same user. Collection owner: ' + self.collection.user.username + ' Transportation owner: ' + self.user.username)

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

class LocationImage(models.Model):
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
    location = models.ForeignKey(Location, related_name='images', on_delete=models.CASCADE)
    is_primary = models.BooleanField(default=False)

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
            
        self.full_clean()  # This calls clean() method
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Remove file from disk when deleting AdventureImage
        if self.image and os.path.isfile(self.image.path):
            os.remove(self.image.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.image.url if self.image else f"Immich ID: {self.immich_id or 'No image'}"
    
class Attachment(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user)
    file = models.FileField(upload_to=PathAndRename('attachments/'),validators=[validate_file_extension])
    location = models.ForeignKey(Location, related_name='attachments', on_delete=models.CASCADE)
    name = models.CharField(max_length=200, null=True, blank=True)

    def delete(self, *args, **kwargs):
        if self.file and os.path.isfile(self.file.path):
            os.remove(self.file.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.file.url

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
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=100, choices=LODGING_TYPES, default='other')
    description = models.TextField(blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)
    link = models.URLField(blank=True, null=True, max_length=2083)
    check_in = models.DateTimeField(blank=True, null=True)
    check_out = models.DateTimeField(blank=True, null=True)
    timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in TIMEZONES], null=True, blank=True)
    reservation_number = models.CharField(max_length=100, blank=True, null=True)
    price = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    is_public = models.BooleanField(default=False)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.check_in and self.check_out and self.check_in > self.check_out:
            raise ValidationError('The start date must be before the end date. Start date: ' + str(self.check_in) + ' End date: ' + str(self.check_out))
        
        if self.collection:
            if self.collection.is_public and not self.is_public:
                raise ValidationError('Lodging associated with a public collection must be public. Collection: ' + self.collection.name + ' Lodging: ' + self.name)
            if self.user != self.collection.user:
                raise ValidationError('Lodging must be associated with collections owned by the same user. Collection owner: ' + self.collection.user.username + ' Lodging owner: ' + self.user.username)

    def __str__(self):
        return self.name