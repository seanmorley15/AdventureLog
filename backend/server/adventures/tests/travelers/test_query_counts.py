"""The visits and notifications lists, and releasing a member, cost a bounded number of queries."""
import shutil
import tempfile

from django.core.files.base import ContentFile
from django.db import connection, transaction
from django.test import override_settings
from django.test.utils import CaptureQueriesContext

from adventures.models import Activity, ContentAttachment, ContentImage, Location, Notification, Visit
from adventures.services import travelers
from adventures.tests.base import AudienceTestBase
from adventures.tests.factories import GPX, PNG


class ListQueryCountTests(AudienceTestBase):
    def _places(self, count):
        for n in range(count):
            place = Location.objects.create(user=self.owner, name=f'Extra {n}', is_public=False)
            place.collections.add(self.trip)
            visit = Visit.objects.create(location=place, start_date='2026-06-01T00:00:00Z')
            visit.travelers.set([self.owner, self.editor])

    def _queries(self, path):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(path)
        self.assertEqual(response.status_code, 200, response.content)
        return len(queries)

    def test_visits_list(self):
        self.as_user(self.editor)
        self._places(3)
        few = self._queries('/api/visits/')
        self._places(15)
        many = self._queries('/api/visits/')
        self.assertLessEqual(many, few, f'{few} queries for 3 visits, {many} for 18')

    def _notes(self, count):
        for n in range(count):
            place = Location.objects.create(user=self.owner, name=f'Note {n}', is_public=False)
            place.collections.add(self.trip)
            visit = Visit.objects.create(location=place, start_date='2026-06-01T00:00:00Z')
            Notification.objects.create(
                user=self.editor, kind=Notification.Kind.VISIT_TRAVELER_ADDED, actor_user=self.owner,
                actor_name='owner', data={
                    'count': 1, 'locations': 1, 'visit_id': str(visit.pk), 'location_id': str(place.pk),
                    'location_name': place.name, 'collection_id': str(self.trip.pk), 'collection_name': 'Lofoten',
                },
            )

    def test_notifications_list(self):
        self.as_user(self.editor)
        self._notes(3)
        few = self._queries('/api/notifications/')
        self._notes(15)
        many = self._queries('/api/notifications/')
        self.assertLessEqual(many, few, f'{few} queries for 3 notifications, {many} for 18')

    def test_suggest(self):
        self.as_user(self.owner)
        self._places(3)
        few = self._queries('/api/locations/suggest/')
        self._places(15)
        many = self._queries('/api/locations/suggest/')
        self.assertLessEqual(many, few, f'{few} queries for 4 places, {many} for 19')


class ReleaseQueryCountTests(AudienceTestBase):
    """
    Releasing a member with copies costs a fixed number of queries per place, however many photos,
    attachments and activities each one holds: copies share files and their rows are inserted in bulk.
    """

    def setUp(self):
        super().setUp()
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root)
        override.enable()
        self.addCleanup(override.disable)

    def _place(self, n, rows):
        place = Location.objects.create(user=self.owner, name=f'Place {n}', is_public=False)
        place.collections.add(self.trip)
        visit = Visit.objects.create(location=place, start_date='2026-06-01T00:00:00Z')
        visit.travelers.set([self.owner, self.editor])
        for i in range(rows):
            ContentImage.objects.create(user=self.owner, image=ContentFile(PNG, name='p.png'), content_object=place)
            ContentImage.objects.create(user=self.editor, image=ContentFile(PNG, name='v.png'), content_object=visit)
            ContentAttachment.objects.create(
                user=self.editor, file=ContentFile(b'x', name='a.txt'), name=f'a{i}', content_object=visit
            )
            run = Activity.objects.create(
                user=self.editor, visit=visit, name=f'Run {i}', gpx_file=ContentFile(GPX, name='r.gpx')
            )
            ContentImage.objects.create(user=self.editor, image=ContentFile(PNG, name='r.png'), content_object=run)

    def _release_queries(self, places, rows):
        """Queries for releasing the editor from ``places`` places of ``rows`` uploads each, then rolled back."""
        try:
            with transaction.atomic():
                for n in range(places):
                    self._place(n, rows)
                with CaptureQueriesContext(connection) as queries:
                    copied = travelers.release_member(self.trip, self.editor, keep_copies=True)
                self.assertEqual(copied, places)
                self.assertEqual(
                    ContentImage.objects.filter(user=self.editor, object_id__in=Location.objects.filter(
                        user=self.editor).values('pk')).count(),
                    places * rows,
                )
                raise _Rollback
        except _Rollback:
            pass
        return len(queries)

    def test_rows_on_a_place_cost_no_extra_queries(self):
        one = self._release_queries(1, 1)
        many = self._release_queries(1, 4)
        self.assertEqual(many, one, f'{one} queries for 1 of each upload, {many} for 4')

    def test_each_place_costs_the_same(self):
        one = self._release_queries(1, 2)
        two = self._release_queries(2, 2)
        five = self._release_queries(5, 2)
        per_place = two - one
        self.assertEqual(five - one, 4 * per_place, f'{one}, {two}, {five} queries for 1, 2, 5 places')


class _Rollback(Exception):
    pass
