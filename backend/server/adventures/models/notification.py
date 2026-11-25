import uuid

from django.db import models

from .base import User


class Notification(models.Model):
    """
    Something that happened to a person, for their inbox. Written once, read by the recipient only.

    ``data`` holds what the recipient could already see when it was written (place and trip names,
    dates, ids); who else was on a visit is never stored. Which keys exist depends on ``kind``.
    """

    class Kind(models.TextChoices):
        VISIT_TRAVELER_ADDED = 'visit_traveler_added', 'Added to a visit'

    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    kind = models.CharField(max_length=40, choices=Kind.choices)
    actor_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, related_name='notifications_sent', blank=True, null=True
    )
    actor_name = models.CharField(max_length=150, blank=True, default='')
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', '-created_at']), models.Index(fields=['user', 'read_at'])]

    def __str__(self):
        return f'{self.kind} for {self.user_id}'
