import uuid

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from core.timezones import validate_timezone

from .base import User, default_user


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

    class CommentAccess(models.TextChoices):
        # Who may comment on the published story. Members comment on the private plan
        # by role instead; this never opens the plan to anyone.
        OFF = 'off', 'Off'
        SIGNED_IN = 'signed_in', 'Signed-in readers'
        LINK_HOLDERS = 'link_holders', 'Signed-in readers and guest links'

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
    comment_access = models.CharField(max_length=20, choices=CommentAccess.choices, default=CommentAccess.OFF)
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
        from adventures.services.day_plan.files import purge_collection_day_files

        with transaction.atomic():
            purge_collection_day_files(self)
            return super().delete(*args, **kwargs)

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
