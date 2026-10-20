import uuid

from django.db import models


from .base import User
from .collection import Collection, CollectionGuestLink


class CollectionComment(models.Model):
    """
    A comment on the private plan (members) or on the published story (readers).

    The two threads never mix: a story response only ever reads ``is_story=True``.
    Replies are one level deep. The author is a user or a guest link; the name is kept
    so a comment still reads correctly after its guest link is gone.
    """

    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='comments')
    is_story = models.BooleanField(default=False)
    day = models.ForeignKey(
        'CollectionItineraryDay', on_delete=models.SET_NULL, related_name='comments', blank=True, null=True
    )
    placement = models.ForeignKey(
        'CollectionItineraryItem', on_delete=models.SET_NULL, related_name='comments', blank=True, null=True
    )
    parent = models.ForeignKey('self', on_delete=models.CASCADE, related_name='replies', blank=True, null=True)
    author_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, related_name='collection_comments', blank=True, null=True
    )
    author_guest = models.ForeignKey(
        CollectionGuestLink, on_delete=models.SET_NULL, related_name='comments', blank=True, null=True
    )
    author_name = models.CharField(max_length=150, blank=True, default='')
    body = models.TextField(max_length=4000)
    mentions = models.ManyToManyField(User, related_name='collection_comment_mentions', blank=True)
    edited_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [models.Index(fields=['collection', 'is_story', 'created_at'])]

    def __str__(self):
        return f"{self.author_name or 'Comment'} on {self.collection}"

class CollectionActivity(models.Model):
    """What changed in a collection, for owners and editors. Never part of the story."""

    class Verb(models.TextChoices):
        DAY_MOVED = 'day_moved', 'Day moved'
        ITEM_MOVED = 'item_moved', 'Item moved'
        ANCHOR_CHANGED = 'anchor_changed', 'Dates changed'
        COMMENT_ADDED = 'comment_added', 'Comment added'
        MEMBER_ADDED = 'member_added', 'Member added'
        MEMBER_REMOVED = 'member_removed', 'Member removed'

    # Membership changes are shown to the owner only.
    OWNER_ONLY_VERBS = (Verb.MEMBER_ADDED, Verb.MEMBER_REMOVED)

    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='activity')
    verb = models.CharField(max_length=20, choices=Verb.choices)
    actor_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, related_name='collection_activity', blank=True, null=True
    )
    actor_name = models.CharField(max_length=150, blank=True, default='')
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['collection', '-created_at'])]

    def __str__(self):
        return f"{self.verb} in {self.collection}"

class CommentInboxState(models.Model):
    """When a user last looked at their new comments."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='comment_inbox')
    seen_at = models.DateTimeField()
