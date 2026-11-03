from unittest.mock import patch

from django.test import TestCase, override_settings

from adventures.models import Location
from core.geo import make_point
from users.models import CustomUser
from worldtravel.models import Country


@override_settings(DISABLE_BACKGROUND_GEOCODE=False)
class LocationGeocodeTriggerTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='geocode-user', email='geocode-user@example.com', password='testpassword123'
        )
        self.country = Country.objects.create(name='Norway', country_code='NO', coordinates=make_point(8.4, 60.4))
        thread_patch = patch('adventures.models.location.threading.Thread')
        self.thread = thread_patch.start()
        self.addCleanup(thread_patch.stop)

    def _create(self, **extra):
        return Location.objects.create(user=self.user, name='Reine', coordinates=make_point(13.0, 67.9), **extra)

    def test_new_place_is_geocoded_once_and_only_after_commit(self):
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            self._create()
            self.assertEqual(self.thread.call_count, 0)

        self.assertEqual(len(callbacks), 1)
        callbacks[0]()
        self.assertEqual(self.thread.call_count, 1)
        self.thread.return_value.start.assert_called_once()

    def test_saving_the_same_instance_again_does_not_geocode_again(self):
        with self.captureOnCommitCallbacks(execute=True):
            location = self._create()
            location.description = 'Second save, as the serializer does after setting the category'
            location.save()

        self.assertEqual(self.thread.call_count, 1)

    def test_saving_a_resolved_place_without_moving_it_does_not_geocode(self):
        location = self._create(country=self.country)
        self.thread.reset_mock()
        stored = Location.objects.get(pk=location.pk)

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            stored.name = 'Reine, renamed'
            stored.save()

        self.assertEqual(callbacks, [])
        self.assertEqual(self.thread.call_count, 0)

    def test_moving_a_place_geocodes_it_again(self):
        location = self._create(country=self.country)
        self.thread.reset_mock()
        stored = Location.objects.get(pk=location.pk)

        with self.captureOnCommitCallbacks(execute=True):
            stored.coordinates = make_point(10.7, 59.9)
            stored.save()

        self.assertEqual(self.thread.call_count, 1)

    def test_a_place_that_was_never_resolved_is_tried_again_on_save(self):
        location = self._create()  # no country: the earlier geocode never filled it in
        self.thread.reset_mock()
        stored = Location.objects.get(pk=location.pk)

        with self.captureOnCommitCallbacks(execute=True):
            stored.name = 'Reine, renamed'
            stored.save()

        self.assertEqual(self.thread.call_count, 1)

    def test_partial_save_that_skips_coordinates_does_not_geocode(self):
        location = self._create()
        self.thread.reset_mock()
        stored = Location.objects.get(pk=location.pk)

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            stored.name = 'Only the name'
            stored.save(update_fields=['name'])

        self.assertEqual(callbacks, [])

    def test_place_without_coordinates_is_not_geocoded(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            Location.objects.create(user=self.user, name='Nowhere in particular')

        self.assertEqual(callbacks, [])
        self.assertEqual(self.thread.call_count, 0)
