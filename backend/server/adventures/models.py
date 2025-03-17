from django.core.exceptions import ValidationError
import os
from typing import Iterable
import uuid
from django.db import models
from django.utils.deconstruct import deconstructible
from adventures.managers import AdventureManager
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.forms import ValidationError
from django_resized import ResizedImageField

def validate_file_extension(value):
    import os
    from django.core.exceptions import ValidationError
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp4', '.mov', '.avi', '.mkv', '.mp3', '.wav', '.flac', '.ogg', '.m4a', '.wma', '.aac', '.opus', '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.zst', '.lz4', '.lzma', '.lzo', '.z', '.tar.gz', '.tar.bz2', '.tar.xz', '.tar.zst', '.tar.lz4', '.tar.lzma', '.tar.lzo', '.tar.z', 'gpx', 'md', 'pdf']
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file extension.')

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
default_user_id = 1  # Replace with an actual user ID

User = get_user_model()

class Visit(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    adventure = models.ForeignKey('Adventure', on_delete=models.CASCADE, related_name='visits')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.start_date > self.end_date:
            raise ValidationError('The start date must be before or equal to the end date.')

    def __str__(self):
        return f"{self.adventure.name} - {self.start_date} to {self.end_date}"

class Adventure(models.Model):
    #id = models.AutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)

    category = models.ForeignKey('Category', on_delete=models.SET_NULL, blank=True, null=True)
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True, null=True)
    activity_types = ArrayField(models.CharField(
        max_length=100), blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)
    link = models.URLField(blank=True, null=True, max_length=2083)
    is_public = models.BooleanField(default=False)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AdventureManager()

    # DEPRECATED FIELDS - TO BE REMOVED IN FUTURE VERSIONS
    # Migrations performed in this version will remove these fields
    # image = ResizedImageField(force_format="WEBP", quality=75, null=True, blank=True, upload_to='images/')
    # date = models.DateField(blank=True, null=True)
    # end_date = models.DateField(blank=True, null=True)
    # type = models.CharField(max_length=100, choices=ADVENTURE_TYPES, default='general')

    def clean(self):
        if self.collection:
            if self.collection.is_public and not self.is_public:
                raise ValidationError('Adventures associated with a public collection must be public. Collection: ' + self.trip.name + ' Adventure: ' + self.name)
            if self.user_id != self.collection.user_id:
                raise ValidationError('Adventures must be associated with collections owned by the same user. Collection owner: ' + self.collection.user_id.username + ' Adventure owner: ' + self.user_id.username)
        if self.category:
            if self.user_id != self.category.user_id:
                raise ValidationError('Adventures must be associated with categories owned by the same user. Category owner: ' + self.category.user_id.username + ' Adventure owner: ' + self.user_id.username)
            
    def save(self, force_insert: bool = False, force_update: bool = False, using: str | None = None, update_fields: Iterable[str] | None = None) -> None:
        """
        Saves the current instance. If the instance is being inserted for the first time, it will be created in the database.
        If it already exists, it will be updated.
        """
        if force_insert and force_update:
            raise ValueError("Cannot force both insert and updating in model saving.")
        if not self.category:
            category, created = Category.objects.get_or_create(
            user_id=self.user_id,
            name='general',
            defaults={
                'display_name': 'General',
                'icon': '🌍'
            }
        )
            self.category = category
            
        return super().save(force_insert, force_update, using, update_fields)

    def __str__(self):
        return self.name

class Collection(models.Model):
    #id = models.AutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
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


    # if connected adventures are private and collection is public, raise an error
    def clean(self):
        if self.is_public and self.pk:  # Only check if the instance has a primary key
            for adventure in self.adventure_set.all():
                if not adventure.is_public:
                    raise ValidationError('Public collections cannot be associated with private adventures. Collection: ' + self.name + ' Adventure: ' + adventure.name)

    def __str__(self):
        return self.name
    
class Transportation(models.Model):
    #id = models.AutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
    type = models.CharField(max_length=100, choices=TRANSPORTATION_TYPES)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
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
            if self.user_id != self.collection.user_id:
                raise ValidationError('Transportations must be associated with collections owned by the same user. Collection owner: ' + self.collection.user_id.username + ' Transportation owner: ' + self.user_id.username)

    def __str__(self):
        return self.name

class Note(models.Model):
    #id = models.AutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
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
            if self.user_id != self.collection.user_id:
                raise ValidationError('Notes must be associated with collections owned by the same user. Collection owner: ' + self.collection.user_id.username + ' Transportation owner: ' + self.user_id.username)

    def __str__(self):
        return self.name
    
class Checklist(models.Model):
    # id = models.AutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
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
            if self.user_id != self.collection.user_id:
                raise ValidationError('Checklists must be associated with collections owned by the same user. Collection owner: ' + self.collection.user_id.username + ' Checklist owner: ' + self.user_id.username)

    def __str__(self):
        return self.name

class ChecklistItem(models.Model):
    #id = models.AutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
    name = models.CharField(max_length=200)
    is_checked = models.BooleanField(default=False)
    checklist = models.ForeignKey('Checklist', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.checklist.is_public and not self.checklist.is_public:
            raise ValidationError('Checklist items associated with a public checklist must be public. Checklist: ' + self.checklist.name + ' Checklist item: ' + self.name)
        if self.user_id != self.checklist.user_id:
            raise ValidationError('Checklist items must be associated with checklists owned by the same user. Checklist owner: ' + self.checklist.user_id.username + ' Checklist item owner: ' + self.user_id.username)

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

class AdventureImage(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
    image = ResizedImageField(
        force_format="WEBP",
        quality=75,
        upload_to=PathAndRename('images/')  # Use the callable class here
    )
    adventure = models.ForeignKey(Adventure, related_name='images', on_delete=models.CASCADE)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return self.image.url
    
class Attachment(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
    file = models.FileField(upload_to=PathAndRename('attachments/'),validators=[validate_file_extension])
    adventure = models.ForeignKey(Adventure, related_name='attachments', on_delete=models.CASCADE)
    name = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.file.url

class Category(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
    name = models.CharField(max_length=200)
    display_name = models.CharField(max_length=200)
    icon = models.CharField(max_length=200, default='🌍')

    class Meta:
        verbose_name_plural = 'Categories'
        unique_together = ['name', 'user_id']

    def clean(self) -> None:
        self.name = self.name.lower().strip()

        return super().clean()
    
    
    def __str__(self):
        return self.name + ' - ' + self.display_name + ' - ' + self.icon
    
class Lodging(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=100, choices=LODGING_TYPES, default='other')
    description = models.TextField(blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)
    link = models.URLField(blank=True, null=True, max_length=2083)
    check_in = models.DateTimeField(blank=True, null=True)
    check_out = models.DateTimeField(blank=True, null=True)
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
        if self.date and self.end_date and self.date > self.end_date:
            raise ValidationError('The start date must be before the end date. Start date: ' + str(self.date) + ' End date: ' + str(self.end_date))
        
        if self.collection:
            if self.collection.is_public and not self.is_public:
                raise ValidationError('Lodging associated with a public collection must be public. Collection: ' + self.collection.name + ' Loging: ' + self.name)
            if self.user_id != self.collection.user_id:
                raise ValidationError('Lodging must be associated with collections owned by the same user. Collection owner: ' + self.collection.user_id.username + ' Lodging owner: ' + self.user_id.username)

    def __str__(self):
        return self.name