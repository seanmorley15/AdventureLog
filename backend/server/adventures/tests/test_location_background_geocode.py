from unittest.mock import patch

from django.test import TestCase, override_settings

from adventures.models import Location
from adventures.utils.geo import make_point
from users.models import CustomUser


@override_settings(DISABLE_BACKGROUND_GEOCODE=False)
@patch('adventures.models.threading.Thread')
class LocationBackgroundGeocodeTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='geocode-thread-user',
            email='geocode-thread-user@example.com',
            password='testpassword123',
        )

    def _create_location(self):
        return Location.objects.create(
            user=self.user,
            name='Hospital Vall d\'Hebron',
            coordinates=make_point(2.140122, 41.427041),
        )

    def test_geocode_waits_for_commit_and_runs_once_per_transaction(self, thread):
        with self.captureOnCommitCallbacks(execute=True):
            location = self._create_location()
            location.save()
            thread.assert_not_called()

        thread.assert_called_once()
        self.assertEqual(thread.call_args.kwargs['args'], (str(location.id),))

    def test_later_save_geocodes_again(self, thread):
        with self.captureOnCommitCallbacks(execute=True):
            location = self._create_location()

        with self.captureOnCommitCallbacks(execute=True):
            location.save()

        self.assertEqual(thread.call_count, 2)
