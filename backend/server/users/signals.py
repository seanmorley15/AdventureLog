from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from allauth.account.models import EmailAddress
from django.db.models.signals import pre_delete

User = get_user_model()

def _sync_user_email(user: AbstractUser):
    from allauth.account.models import EmailAddress  # local import to avoid early import issues

    # Prefer the primary email if it exists
    primary = EmailAddress.objects.filter(user=user, primary=True).first()
    if primary:
        if user.email != primary.email:
            user.email = primary.email
            user.save(update_fields=['email'])
        return

    # Fallback: if any email exists, use the first; if none, leave user.email unchanged
    any_email = EmailAddress.objects.filter(user=user).order_by('id').first()
    if any_email and user.email != any_email.email:
        user.email = any_email.email
        user.save(update_fields=['email'])

@receiver(post_save)
def emailaddress_post_save(sender, instance, **kwargs):
    # Only react to allauth EmailAddress saves
    try:
        from allauth.account.models import EmailAddress
    except Exception:
        return
    if sender is EmailAddress:
        _sync_user_email(instance.user)

@receiver(post_delete)
def emailaddress_post_delete(sender, instance, **kwargs):
    # Only react to allauth EmailAddress deletes
    try:
        from allauth.account.models import EmailAddress
    except Exception:
        return
    if sender is EmailAddress:
        _sync_user_email(instance.user)

# Prevent deleting the last email address for a user
@receiver(pre_delete, sender=EmailAddress)
def prevent_deleting_last_email(sender, instance, using, **kwargs):
    user = instance.user
    email_count = EmailAddress.objects.filter(user=user).count()
    if email_count <= 1:
        raise ValueError("Cannot delete the last email address of a user.")