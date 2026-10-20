import os
import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db import models as gis_models
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.deconstruct import deconstructible
from django_resized import ResizedImageField


from .base import User, default_user


def validate_file_extension(value):
    import os
    from django.core.exceptions import ValidationError
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp4', '.mov', '.avi', '.mkv', '.mp3', '.wav', '.flac', '.ogg', '.m4a', '.wma', '.aac', '.opus', '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.zst', '.lz4', '.lzma', '.lzo', '.z', '.tar.gz', '.tar.bz2', '.tar.xz', '.tar.zst', '.tar.lz4', '.tar.lzma', '.tar.lzo', '.tar.z', '.gpx', '.md']
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file extension.')

@deconstructible(path="adventures.models.PathAndRename")
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
            # Every Immich thumbnail request looks its photo records up by this.
            models.Index(fields=["immich_id"], name="contentimage_immich_idx"),
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

    def __str__(self):
        content_name = getattr(self.content_object, 'name', 'Unknown')
        return f"Attachment for {self.content_type.model}: {content_name}"
