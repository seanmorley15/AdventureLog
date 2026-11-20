"""The small background tasks: when they retry, what they skip, and the schedule that replaced cron."""

from smtplib import SMTPException
from types import SimpleNamespace

from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import TestCase
from django.utils import timezone
from procrastinate.contrib.django import app

from adventures.models import Collection, CollectionComment, ContentImage, Location
from adventures.services.geocoding.assignment import GeocodeUnavailable
from adventures.tasks import delete_stored_file, geocode_location, send_mention_email_task
from core.testing import make_user


def decision(task, exception, attempts):
    """What the queue does when ``task`` raised ``exception`` on its ``attempts``-th run."""
    return task.retry_strategy.get_retry_decision(exception=exception, job=SimpleNamespace(attempts=attempts))


def wait_seconds(task, exception, attempts):
    """Seconds the queue waits before the next run (whole seconds: the decision stores a timestamp)."""
    retry_at = decision(task, exception, attempts).retry_at
    return round((retry_at - timezone.now()).total_seconds() / 10) * 10


class RetryPolicyTests(TestCase):
    def test_geocoding_is_retried_with_growing_waits_and_then_given_up(self):
        waits = [wait_seconds(geocode_location, GeocodeUnavailable(), n) for n in (1, 2, 3, 4)]

        self.assertEqual(waits, [60, 90, 120, 150])
        self.assertIsNone(decision(geocode_location, GeocodeUnavailable(), 5))

    def test_a_mail_server_that_is_down_is_retried_but_a_bug_is_not(self):
        self.assertIsNotNone(decision(send_mention_email_task, SMTPException('down'), 1))
        self.assertIsNotNone(decision(send_mention_email_task, ConnectionRefusedError(), 1))
        self.assertIsNone(decision(send_mention_email_task, KeyError('bug'), 1))
        self.assertIsNone(decision(send_mention_email_task, SMTPException('down'), 5))

    def test_a_failing_storage_is_retried_three_times(self):
        self.assertIsNotNone(decision(delete_stored_file, OSError('disk'), 2))
        self.assertIsNone(decision(delete_stored_file, OSError('disk'), 3))


class MentionEmailTaskTests(TestCase):
    def test_a_comment_or_person_deleted_since_it_was_queued_is_skipped(self):
        owner = make_user('mention-owner')
        trip = Collection.objects.create(user=owner, name='Trip')
        comment = CollectionComment.objects.create(
            collection=trip, body='@mention-owner hi', author_user=owner, author_name='mention-owner'
        )
        person = make_user('mention-person')

        comment_id = str(comment.pk)
        comment.delete()

        send_mention_email_task.func(comment_id=comment_id, user_id=str(person.pk))  # comment is gone
        send_mention_email_task.func(comment_id=comment_id, user_id='0')  # and so is the person


class DeleteStoredFileTaskTests(TestCase):
    def test_a_file_another_row_still_uses_is_kept_and_an_unused_one_is_deleted(self):
        user = make_user('file-owner')
        place = Location.objects.create(user=user, name='Place')
        name = default_storage.save('images/shared-test.png', ContentFile(b'png'))
        self.addCleanup(lambda: default_storage.exists(name) and default_storage.delete(name))
        ContentImage.objects.create(
            user=user, content_type=ContentType.objects.get_for_model(Location), object_id=place.id, image=name
        )

        delete_stored_file.func(model_label='adventures.ContentImage', field_name='image', name=name)
        self.assertTrue(default_storage.exists(name))

        ContentImage.objects.all().delete()
        delete_stored_file.func(model_label='adventures.ContentImage', field_name='image', name=name)
        self.assertFalse(default_storage.exists(name))


class ScheduleTests(TestCase):
    """Cron is gone from the container; the worker runs these on its own schedule (UTC)."""

    def test_every_scheduled_task_is_registered(self):
        schedule = {
            task.task.name: task.cron for task in app.periodic_registry.periodic_tasks.values()
        }

        self.assertEqual(schedule['adventures.sync_visited_regions'], '0 0 * * *')
        self.assertEqual(schedule['jobs.clearsessions'], '15 3 * * 0')
        self.assertEqual(schedule['jobs.prune_jobs'], '0 * * * *')
        self.assertEqual(schedule['jobs.retry_stalled_jobs'], '*/10 * * * *')
        self.assertEqual(schedule['jobs.remove_old_jobs'], '30 4 * * *')
