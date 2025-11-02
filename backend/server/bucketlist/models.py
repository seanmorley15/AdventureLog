import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericRelation

User = get_user_model()

STATUS_CHOICES = (
    ('planned', 'Planned'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
)


class BucketItem(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    tags = ArrayField(models.CharField(max_length=100), blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    # Optional link to an existing Location
    location = models.ForeignKey('adventures.Location', on_delete=models.SET_NULL, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Allow attaching images/attachments via existing generic models in the adventures app
    images = GenericRelation('adventures.ContentImage', related_query_name='bucketitem')
    attachments = GenericRelation('adventures.ContentAttachment', related_query_name='bucketitem')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
