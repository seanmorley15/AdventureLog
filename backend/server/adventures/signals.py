from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from threading import local
import logging

from adventures.models import Location, Visit

logger = logging.getLogger(__name__)

# Thread-local storage for current user (used by audit logging)
_thread_locals = local()


def set_current_user(user):
    """Called by middleware to set the current user for audit logging."""
    _thread_locals.user = user


def get_current_user():
    """Get the current user from thread-local storage."""
    return getattr(_thread_locals, 'user', None)


@receiver(m2m_changed, sender=Location.collections.through)
def update_adventure_publicity(sender, instance, action, **kwargs):
    """
    Signal handler to update adventure publicity when collections are added/removed
    This function checks if the adventure's collections contain any public collection.
    """
    if not isinstance(instance, Location):
        return
    # Only process when collections are added or removed
    if action in ('post_add', 'post_remove', 'post_clear'):
        collections = instance.collections.all()
        
        if collections.exists():
            # If any collection is public, make the adventure public
            has_public_collection = collections.filter(is_public=True).exists()
            
            if has_public_collection and not instance.is_public:
                instance.is_public = True
                instance.save(update_fields=['is_public'])
            elif not has_public_collection and instance.is_public:
                instance.is_public = False
                instance.save(update_fields=['is_public'])


@receiver(post_delete)
def _remove_collection_itinerary_items_on_object_delete(sender, instance, **kwargs):
    """
    When any model instance is deleted, remove any CollectionItineraryItem that
    refers to it via the GenericForeignKey (matches by ContentType and object_id).

    This ensures that if a referenced item (e.g. a `Location`, `Visit`, `Transportation`,
    `Note`, etc.) is deleted, the itinerary entry that pointed to it is also removed.
    """
    # Avoid acting when a CollectionItineraryItem itself is deleted
    # to prevent needless extra queries.
    if sender.__name__ == 'CollectionItineraryItem':
        return

    # Resolve the content type for the model that was deleted
    try:
        ct = ContentType.objects.get_for_model(sender)
    except Exception:
        return

    # Import here to avoid circular import problems at module import time
    from adventures.models import CollectionItineraryItem

    # Try matching the primary key in its native form first, then as a string.
    # CollectionItineraryItem.object_id is a UUIDField in the model, but some
    # senders might have different PK representations; handle both safely.
    pk = instance.pk
    deleted = False
    try:
        qs = CollectionItineraryItem.objects.filter(content_type=ct, object_id=pk)
        if qs.exists():
            qs.delete()
            deleted = True
    except Exception:
        pass

    if not deleted:
        try:
            CollectionItineraryItem.objects.filter(content_type=ct, object_id=str(pk)).delete()
        except Exception:
            # If deletion fails for any reason, do nothing; we don't want to
            # raise errors during another model's delete.
            pass


# ---------------------------------------------------------------------------
# Audit Logging for Collaborative Mode
# ---------------------------------------------------------------------------

def _get_auditable_models():
    """Returns list of models that should be audited in collaborative mode."""
    from adventures.models import (
        Location, Collection, Category, Visit, ContentImage, ContentAttachment,
        Note, Transportation, Lodging, CollectionItineraryItem
    )
    return [Location, Collection, Category, Visit, ContentImage, ContentAttachment, Note, Transportation, Lodging, CollectionItineraryItem]


@receiver(pre_save)
def track_changes_before_save(sender, instance, **kwargs):
    """Store old values before save for comparison in audit log."""
    if not getattr(settings, 'COLLABORATIVE_MODE', False):
        return

    auditable_models = _get_auditable_models()
    if sender not in auditable_models:
        return

    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._old_values = {
                field.name: getattr(old_instance, field.name)
                for field in sender._meta.fields
            }
        except sender.DoesNotExist:
            instance._old_values = {}


def _normalize_value(value):
    """Normalize empty-equivalent values for comparison to avoid false positives."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return None if stripped == '' else stripped
    return value


def _values_are_equal(old_value, new_value):
    """Compare two values with normalization for empty equivalents."""
    normalized_old = _normalize_value(old_value)
    normalized_new = _normalize_value(new_value)
    return normalized_old == normalized_new


# Fields to exclude from audit logging
# - System fields: auto-managed timestamps
# - Derived fields: computed from other data (e.g., average_rating from visits)
AUDIT_EXCLUDED_FIELDS = {
    'updated_at',
    'created_at',
    'average_rating',  # Computed from visit ratings, not user-edited
}


@receiver(post_save)
def log_save_to_audit(sender, instance, created, **kwargs):
    """Log create/update actions to AuditLog in collaborative mode."""
    if not getattr(settings, 'COLLABORATIVE_MODE', False):
        return

    auditable_models = _get_auditable_models()
    if sender not in auditable_models:
        return

    from adventures.models import AuditLog

    user = get_current_user()
    action = 'create' if created else 'update'

    changes = {}
    if not created and hasattr(instance, '_old_values'):
        for field, old_value in instance._old_values.items():
            # Skip excluded fields (system/derived fields)
            if field in AUDIT_EXCLUDED_FIELDS:
                continue
            new_value = getattr(instance, field)
            # Use normalized comparison to avoid false positives
            if not _values_are_equal(old_value, new_value):
                changes[field] = {'old': str(old_value), 'new': str(new_value)}

    # Only log updates if there were actual changes
    if action == 'update' and not changes:
        return

    AuditLog.objects.create(
        user=user,
        action=action,
        content_type=ContentType.objects.get_for_model(sender),
        object_id=instance.pk,
        object_repr=str(instance)[:200],
        changes=changes
    )


@receiver(post_delete)
def log_delete_to_audit(sender, instance, **kwargs):
    """Log delete actions to AuditLog in collaborative mode."""
    if not getattr(settings, 'COLLABORATIVE_MODE', False):
        return

    auditable_models = _get_auditable_models()
    if sender not in auditable_models:
        return

    from adventures.models import AuditLog

    AuditLog.objects.create(
        user=get_current_user(),
        action='delete',
        content_type=ContentType.objects.get_for_model(sender),
        object_id=instance.pk,
        object_repr=str(instance)[:200],
        changes={}
    )


# ---------------------------------------------------------------------------
# Auto-mark cities/regions as visited when a Visit is created
# ---------------------------------------------------------------------------

def _get_visit_coordinates(visit):
    """
    Get lat/lon from the visit's parent (location, transportation, or lodging).
    For transportation, uses destination coordinates.
    """
    from adventures.models import Location, Transportation, Lodging

    try:
        if visit.location_id and visit.location:
            return visit.location.latitude, visit.location.longitude
        elif visit.transportation_id and visit.transportation:
            # Use destination as the "visited" place
            return visit.transportation.destination_latitude, visit.transportation.destination_longitude
        elif visit.lodging_id and visit.lodging:
            return visit.lodging.latitude, visit.lodging.longitude
    except (Location.DoesNotExist, Transportation.DoesNotExist, Lodging.DoesNotExist):
        pass
    return None, None


def mark_city_region_visited(user, lat, lon):
    """
    Given coordinates, find the city/region and mark them as visited for the user.
    Returns tuple of (city_marked, region_marked) booleans.
    """
    from worldtravel.models import VisitedCity, VisitedRegion
    from adventures.geocoding import reverse_geocode

    if lat is None or lon is None:
        return False, False

    try:
        geo_data = reverse_geocode(float(lat), float(lon), user)
    except Exception as e:
        logger.warning(f"Reverse geocode failed for ({lat}, {lon}): {e}")
        return False, False

    if 'error' in geo_data:
        logger.debug(f"Reverse geocode returned error: {geo_data['error']}")
        return False, False

    city_marked = False
    region_marked = False

    # Mark region as visited
    region_id = geo_data.get('region_id')
    if region_id:
        from worldtravel.models import Region
        try:
            region = Region.objects.get(id=region_id)
            if not VisitedRegion.objects.filter(user=user, region=region).exists():
                VisitedRegion.objects.create(user=user, region=region)
                region_marked = True
                logger.info(f"Auto-marked region {region.name} as visited for user {user.username}")
        except Region.DoesNotExist:
            pass

    # Mark city as visited
    city_id = geo_data.get('city_id')
    if city_id:
        from worldtravel.models import City
        try:
            city = City.objects.get(id=city_id)
            if not VisitedCity.objects.filter(user=user, city=city).exists():
                VisitedCity.objects.create(user=user, city=city)
                city_marked = True
                logger.info(f"Auto-marked city {city.name} as visited for user {user.username}")
        except City.DoesNotExist:
            pass

    return city_marked, region_marked


@receiver(post_save, sender=Visit)
def auto_mark_visited_on_visit_create(sender, instance, created, **kwargs):
    """
    When a Visit is created, automatically mark the corresponding city/region as visited.
    """
    if not created:
        return

    user = instance.user
    if not user:
        return

    lat, lon = _get_visit_coordinates(instance)
    if lat is not None and lon is not None:
        mark_city_region_visited(user, lat, lon)


# ---------------------------------------------------------------------------
# Update cached average_rating when Visit ratings change
# ---------------------------------------------------------------------------

def _update_parent_average_rating(visit):
    """
    Recalculate and update the average_rating on the visit's parent (Location, Transportation, or Lodging).
    """
    from adventures.models import Location, Transportation, Lodging

    # Safely get parent - it may have been deleted in a CASCADE
    parent = None
    try:
        if visit.location_id:
            parent = visit.location
        elif visit.transportation_id:
            parent = visit.transportation
        elif visit.lodging_id:
            parent = visit.lodging
    except (Location.DoesNotExist, Transportation.DoesNotExist, Lodging.DoesNotExist):
        # Parent was deleted, nothing to update
        return

    if not parent:
        return

    # Get all visit ratings for this parent
    ratings = [v.rating for v in parent.visits.all() if v.rating is not None]

    if ratings:
        avg = round(sum(ratings) / len(ratings), 2)
    else:
        avg = None

    # Only update if changed to avoid unnecessary writes
    if parent.average_rating != avg:
        parent.average_rating = avg
        parent.save(update_fields=['average_rating'])


@receiver(post_save, sender=Visit)
def update_average_rating_on_visit_save(sender, instance, **kwargs):
    """Update parent's average_rating when a visit is saved."""
    _update_parent_average_rating(instance)


@receiver(post_delete, sender=Visit)
def update_average_rating_on_visit_delete(sender, instance, **kwargs):
    """Update parent's average_rating when a visit is deleted."""
    _update_parent_average_rating(instance)
