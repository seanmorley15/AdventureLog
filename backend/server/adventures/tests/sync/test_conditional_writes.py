"""
``If-Match`` on writes: a client that read a record at some version can say "only change it if it is
still that version". The web app sends no header and is unaffected.
"""

from datetime import date

from rest_framework.test import APITestCase

from adventures.models import Checklist, Location, Note, Visit
from core.testing import make_user


class ConditionalWriteTests(APITestCase):
    def setUp(self):
        self.user = make_user('sync-owner')
        self.client.force_authenticate(user=self.user)
        self.place = Location.objects.create(user=self.user, name='Reine', description='first')

    def url(self):
        return f'/api/locations/{self.place.id}/'

    def read(self):
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        return response

    def test_reads_and_writes_carry_an_etag(self):
        read = self.read()
        self.assertRegex(read['ETag'], r'^"\d+"$')

        patched = self.client.patch(self.url(), {'description': 'second'}, format='json', HTTP_IF_MATCH=read['ETag'])
        self.assertEqual(patched.status_code, 200, patched.content)
        self.assertRegex(patched['ETag'], r'^"\d+"$')
        self.assertNotEqual(patched['ETag'], read['ETag'])

    def test_creating_returns_the_etag_too(self):
        response = self.client.post('/api/locations/', {'name': 'New'}, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertRegex(response['ETag'], r'^"\d+"$')

    def test_the_etag_returned_by_a_write_is_the_one_the_next_read_shows(self):
        patched = self.client.patch(self.url(), {'description': 'second'}, format='json')

        self.assertEqual(patched['ETag'], self.read()['ETag'])

    def test_a_write_with_the_current_version_goes_through(self):
        etag = self.read()['ETag']

        response = self.client.patch(self.url(), {'description': 'second'}, format='json', HTTP_IF_MATCH=etag)

        self.assertEqual(response.status_code, 200)
        self.place.refresh_from_db()
        self.assertEqual(self.place.description, 'second')

    def test_a_write_with_an_old_version_is_refused_and_changes_nothing(self):
        stale = self.read()['ETag']
        self.client.patch(self.url(), {'description': 'someone else'}, format='json')

        response = self.client.patch(self.url(), {'description': 'mine'}, format='json', HTTP_IF_MATCH=stale)

        self.assertEqual(response.status_code, 412)
        self.assertEqual(response.json()['code'], 'precondition_failed')
        self.place.refresh_from_db()
        self.assertEqual(self.place.description, 'someone else')

    def test_the_refusal_carries_the_current_record_and_its_tag(self):
        stale = self.read()['ETag']
        self.client.patch(self.url(), {'description': 'someone else'}, format='json')

        response = self.client.patch(self.url(), {'description': 'mine'}, format='json', HTTP_IF_MATCH=stale)

        self.assertEqual(response.json()['current']['description'], 'someone else')
        self.assertEqual(response['ETag'], self.read()['ETag'])

    def test_a_write_without_the_header_still_overwrites(self):
        self.client.patch(self.url(), {'description': 'someone else'}, format='json')

        response = self.client.patch(self.url(), {'description': 'web edit'}, format='json')

        self.assertEqual(response.status_code, 200)

    def test_a_star_means_any_existing_record(self):
        response = self.client.patch(self.url(), {'description': 'x'}, format='json', HTTP_IF_MATCH='*')

        self.assertEqual(response.status_code, 200)

    def test_delete_is_conditional_too(self):
        stale = self.read()['ETag']
        self.client.patch(self.url(), {'description': 'changed'}, format='json')

        refused = self.client.delete(self.url(), HTTP_IF_MATCH=stale)
        self.assertEqual(refused.status_code, 412)
        self.assertTrue(Location.objects.filter(pk=self.place.pk).exists())

        allowed = self.client.delete(self.url(), HTTP_IF_MATCH=self.read()['ETag'])
        self.assertEqual(allowed.status_code, 204)
        self.assertFalse(Location.objects.filter(pk=self.place.pk).exists())

    def test_a_record_that_is_gone_is_a_404_not_a_412(self):
        etag = self.read()['ETag']
        self.place.delete()

        response = self.client.patch(self.url(), {'description': 'x'}, format='json', HTTP_IF_MATCH=etag)

        self.assertEqual(response.status_code, 404)

    def test_someone_elses_record_is_still_a_404(self):
        other = Location.objects.create(user=make_user('someone-else'), name='Private', is_public=False)

        response = self.client.patch(
            f'/api/locations/{other.id}/', {'description': 'x'}, format='json', HTTP_IF_MATCH='*'
        )

        self.assertEqual(response.status_code, 404)

    def test_a_refused_write_leaves_the_database_untouched(self):
        stale = self.read()['ETag']
        self.client.patch(self.url(), {'name': 'Renamed'}, format='json')

        self.client.patch(self.url(), {'name': 'Mine', 'description': 'mine'}, format='json', HTTP_IF_MATCH=stale)

        self.place.refresh_from_db()
        self.assertEqual((self.place.name, self.place.description), ('Renamed', 'first'))


class OtherResourcesTests(APITestCase):
    """Visits, notes and checklists follow the same rules."""

    def setUp(self):
        self.user = make_user('sync-other')
        self.client.force_authenticate(user=self.user)
        self.place = Location.objects.create(user=self.user, name='Reine')

    def check(self, url, field, first, second):
        etag = self.client.get(url)['ETag']
        self.client.patch(url, {field: first}, format='json')

        refused = self.client.patch(url, {field: second}, format='json', HTTP_IF_MATCH=etag)
        accepted = self.client.patch(
            url, {field: second}, format='json', HTTP_IF_MATCH=self.client.get(url)['ETag']
        )

        self.assertEqual(refused.status_code, 412, refused.content)
        self.assertEqual(accepted.status_code, 200, accepted.content)

    def test_visits(self):
        visit = Visit.objects.create(location=self.place, start_date='2026-06-01T00:00:00Z')
        self.check(f'/api/visits/{visit.id}/', 'notes', 'a', 'b')

    def test_notes(self):
        note = Note.objects.create(user=self.user, name='Pack', content='x')
        self.check(f'/api/notes/{note.id}/', 'content', 'a', 'b')

    def test_checklists(self):
        checklist = Checklist.objects.create(user=self.user, name='Gear', date=date(2026, 6, 1))
        self.check(f'/api/checklists/{checklist.id}/', 'name', 'a', 'b')
