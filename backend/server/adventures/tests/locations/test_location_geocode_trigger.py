from unittest.mock import patch

from django.db import transaction
from django.test import TestCase, override_settings

from adventures.models import Location
from adventures.tasks import geocode_location
from core.geo import make_point
from jobs.testing import discard_pending_jobs, queued_jobs, run_pending_jobs
from users.models import CustomUser
from worldtravel.models import Country

TASK = 'adventures.geocode_location'


@override_settings(DISABLE_BACKGROUND_GEOCODE=False)
class LocationGeocodeTriggerTests(TestCase):
    """Saving a place queues a job that fills in its country, region and city."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='geocode-user', email='geocode-user@example.com', password='testpassword123'
        )
        self.country = Country.objects.create(name='Norway', country_code='NO', coordinates=make_point(8.4, 60.4))

    def _create(self, **extra):
        return Location.objects.create(user=self.user, name='Reine', coordinates=make_point(13.0, 67.9), **extra)

    def _queued(self):
        return queued_jobs(TASK).count()

    def test_new_place_is_queued_once_with_its_id(self):
        location = self._create()

        self.assertEqual(self._queued(), 1)
        self.assertEqual(queued_jobs(TASK)[0].args, {'location_id': str(location.id)})

    def test_nothing_is_queued_when_the_save_is_rolled_back(self):
        try:
            with transaction.atomic():
                self._create()
                raise RuntimeError('roll back')
        except RuntimeError:
            pass

        self.assertEqual(self._queued(), 0)

    def test_saving_the_same_instance_again_does_not_queue_again(self):
        location = self._create()
        discard_pending_jobs()
        location.description = 'Second save, as the serializer does after setting the category'
        location.save()

        self.assertEqual(self._queued(), 0)

    def test_saving_a_resolved_place_without_moving_it_does_not_geocode(self):
        location = self._create(country=self.country)
        discard_pending_jobs()
        stored = Location.objects.get(pk=location.pk)

        stored.name = 'Reine, renamed'
        stored.save()

        self.assertEqual(self._queued(), 0)

    def test_moving_a_place_geocodes_it_again(self):
        location = self._create(country=self.country)
        discard_pending_jobs()
        stored = Location.objects.get(pk=location.pk)

        stored.coordinates = make_point(10.7, 59.9)
        stored.save()

        self.assertEqual(self._queued(), 1)

    def test_moving_a_place_twice_before_the_job_runs_shares_one_job(self):
        location = self._create(country=self.country)
        discard_pending_jobs()

        for point in (make_point(10.7, 59.9), make_point(5.3, 60.4)):
            stored = Location.objects.get(pk=location.pk)
            stored.coordinates = point
            stored.save()

        self.assertEqual(self._queued(), 1)

    def test_a_place_that_was_never_resolved_is_tried_again_on_save(self):
        location = self._create()  # no country: the earlier geocode never filled it in
        discard_pending_jobs()
        stored = Location.objects.get(pk=location.pk)

        stored.name = 'Reine, renamed'
        stored.save()

        self.assertEqual(self._queued(), 1)

    def test_partial_save_that_skips_coordinates_does_not_geocode(self):
        location = self._create()
        discard_pending_jobs()
        stored = Location.objects.get(pk=location.pk)

        stored.name = 'Only the name'
        stored.save(update_fields=['name'])

        self.assertEqual(self._queued(), 0)

    def test_place_without_coordinates_is_not_geocoded(self):
        Location.objects.create(user=self.user, name='Nowhere in particular')

        self.assertEqual(self._queued(), 0)

    def test_a_queue_that_cannot_be_written_never_fails_the_save(self):
        with patch.object(geocode_location, 'configure', side_effect=RuntimeError('queue down')):
            with self.assertLogs('adventures.models.location', 'ERROR'):
                location = self._create()

        self.assertTrue(Location.objects.filter(pk=location.pk).exists())

    def test_the_job_geocodes_the_place_and_asks_to_hear_when_no_provider_answers(self):
        location = self._create()

        with patch('adventures.services.geocoding.assignment.geocode_and_assign_location') as geocode:
            run_pending_jobs(TASK)

        geocode.assert_called_once_with(str(location.id), raise_if_unavailable=True)
