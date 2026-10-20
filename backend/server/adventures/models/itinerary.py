import uuid

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from core.timezones import validate_timezone

from .collection import Collection
from .location import Visit


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
        indexes = [
            # Looked up whenever a place, lodging, note, etc. is deleted.
            models.Index(fields=["content_type", "object_id"], name="itinerary_item_target_idx"),
        ]
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
