from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from adventures.models import Location

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
