"""Lists have a ceiling, the account previews are rate limited, and repeated additions do not spam."""
import uuid

from django.core.cache import cache
from django.test import override_settings

from adventures.models import Notification, Visit
from adventures.tests.base import AudienceTestBase
from jobs.testing import queued_jobs


def _uuids(n):
    return [str(uuid.uuid4()) for _ in range(n)]


class ListBoundsTests(AudienceTestBase):
    def test_traveler_uuids_over_100_is_400(self):
        visit = Visit.objects.create(location=self.hut, start_date='2026-06-01T00:00:00Z')
        visit.travelers.set([self.owner])
        self.as_user(self.owner)
        response = self.client.patch(f'/api/visits/{visit.id}/', {'traveler_uuids': _uuids(101)}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('no more than 100', str(response.data['fields']['traveler_uuids']))
        response = self.client.post(
            f'/api/collections/{self.trip.id}/itinerary-items/{self.stop.id}/log-visit/',
            {'traveler_uuids': _uuids(101)}, format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('no more than 100', str(response.data['fields']['traveler_uuids']))

    def test_user_uuids_over_100_is_400(self):
        self.as_user(self.owner)
        response = self.client.post(
            f'/api/collections/{self.trip.id}/add-travelers/', {'user_uuids': _uuids(101)}, format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('no more than 100', str(response.data['fields']['user_uuids']))

    def test_mark_read_ids_over_1000_is_400(self):
        self.as_user(self.owner)
        response = self.client.post('/api/notifications/mark-read/', {'ids': _uuids(1001)}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('no more than 1000', str(response.data['fields']['ids']))
        response = self.client.post('/api/notifications/mark-read/', {'ids': _uuids(1000)}, format='json')
        self.assertEqual(response.status_code, 200)


class AccountPreviewThrottleTests(AudienceTestBase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def tearDown(self):
        cache.clear()
        super().tearDown()

    @override_settings(ENABLE_RATE_LIMITS=True, RATE_LIMIT_RATES={'account_preview': '2/minute'})
    def test_previews_are_rate_limited_and_the_account_is_not(self):
        self.as_user(self.editor)
        for path in ('/api/account/deletion-preview/', '/api/account/privacy-preview/'):
            cache.clear()
            codes = [self.client.get(path).status_code for _ in range(3)]
            self.assertEqual(codes, [200, 200, 429], path)
        cache.clear()
        self.assertEqual({self.client.get('/api/account/').status_code for _ in range(4)}, {200})

    def test_no_limit_unless_rate_limits_are_on(self):
        self.as_user(self.editor)
        self.assertEqual({self.client.get('/api/account/privacy-preview/').status_code for _ in range(5)}, {200})


class RepeatedAdditionTests(AudienceTestBase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.visit = Visit.objects.create(location=self.hut, start_date='2026-06-01T00:00:00Z')
        self.visit.travelers.set([self.owner])
        self.as_user(self.owner)

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def _set(self, *people):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                f'/api/visits/{self.visit.id}/', {'traveler_uuids': [str(p.uuid) for p in people]}, format='json'
            )
        self.assertEqual(response.status_code, 200, response.data)

    @override_settings(SMTP_CONFIGURED=True)
    def test_removing_and_adding_again_tells_them_once(self):
        for _ in range(3):
            self._set(self.owner, self.editor)
            self._set(self.owner)
        self._set(self.owner, self.editor)
        self.assertEqual(queued_jobs('adventures.send_traveler_added_email').count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.editor).count(), 1)

    @override_settings(SMTP_CONFIGURED=True)
    def test_another_person_or_visit_is_told(self):
        self._set(self.owner, self.editor)
        self._set(self.owner, self.editor, self.viewer)
        other = Visit.objects.create(location=self.hut, start_date='2026-06-02T00:00:00Z')
        other.travelers.set([self.owner])
        with self.captureOnCommitCallbacks(execute=True):
            self.client.patch(
                f'/api/visits/{other.id}/', {'traveler_uuids': [str(self.owner.uuid), str(self.editor.uuid)]},
                format='json',
            )
        self.assertEqual(queued_jobs('adventures.send_traveler_added_email').count(), 3)
        # Someone else adding them to the same visit is told too.
        self._set(self.owner)
        self.as_user(self.editor)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                f'/api/visits/{self.visit.id}/', {'traveler_uuids': [str(self.owner.uuid), str(self.viewer.uuid)]},
                format='json',
            )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(queued_jobs('adventures.send_traveler_added_email').count(), 4)
        self.assertEqual(Notification.objects.get(user=self.viewer).actor_user, self.editor)
