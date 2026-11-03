import uuid

from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.gis.db import models as gis_models
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from adventures.utils.sports_types import SPORT_TYPE_CHOICES
from core.timezones import TIMEZONES

from .base import User, default_user
from .location import Location, Visit
from .media import PathAndRename, validate_file_extension


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
