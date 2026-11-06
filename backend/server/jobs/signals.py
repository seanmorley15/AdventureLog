from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import BackgroundJob
from .storage import delete_names


@receiver(post_delete, sender=BackgroundJob)
def delete_files_of_deleted_job(sender, instance, **kwargs):
    """A job's files go with its row: a user's delete, the admin, or the user's account being deleted."""
    names = (instance.input_file, instance.result_file)
    transaction.on_commit(lambda: delete_names(*names))
