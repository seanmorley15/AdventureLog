"""
Paths that take someone off visits they read a moment earlier (copies, leaving, saving a location)
finish when that already happened meanwhile, instead of failing the whole change.
"""
from unittest.mock import patch

from django.db.models.signals import m2m_changed, post_save

from adventures.models import Location, Visit
from adventures.services import travelers
from adventures.services.locations import copy as copying
from adventures.tests.base import AudienceTestBase


class InternalPathRaceTests(AudienceTestBase):
    def _visit(self, who, start='2026-06-01T00:00:00Z'):
        visit = Visit.objects.create(location=self.hut, start_date=start)
        visit.travelers.set(who)
        return visit

    def test_detach_if_traveler_tolerates_a_visit_already_left_or_gone(self):
        visit = self._visit([self.owner])
        self.assertEqual(travelers.detach_if_traveler(visit, self.editor), 'kept')
        Visit.objects.filter(pk=visit.pk).delete()
        self.assertEqual(travelers.detach_if_traveler(visit, self.editor), 'deleted')

    def test_take_my_visits_when_taken_off_meanwhile(self):
        visit = self._visit([self.owner, self.editor])
        real = copying.copy_visit_uploads

        def and_someone_removes_them(original, moved, user):
            real(original, moved, user)
            Visit.objects.get(pk=original.pk).travelers.remove(user)

        with patch.object(copying, 'copy_visit_uploads', side_effect=and_someone_removes_them):
            copy = travelers.take_my_visits(self.hut, self.editor)
        self.assertEqual(copy.visits.count(), 1)
        self.assertEqual(list(visit.travelers.values_list('username', flat=True)), ['owner'])

    def test_leaving_without_copies_when_taken_off_one_visit_meanwhile(self):
        first = self._visit([self.owner, self.editor])
        second = self._visit([self.owner, self.editor], '2026-06-02T00:00:00Z')

        def also_take_them_off_the_other(sender, instance, action, pk_set=None, **kwargs):
            if action == 'post_remove' and self.editor.pk in (pk_set or ()):
                other = second if instance.pk == first.pk else first
                m2m_changed.disconnect(also_take_them_off_the_other, sender=Visit.travelers.through)
                Visit.objects.get(pk=other.pk).travelers.remove(self.editor)

        m2m_changed.connect(also_take_them_off_the_other, sender=Visit.travelers.through)
        try:
            travelers.release_member(self.trip, self.editor, keep_copies=False)
        finally:
            m2m_changed.disconnect(also_take_them_off_the_other, sender=Visit.travelers.through)
        self.assertFalse(Visit.objects.filter(travelers=self.editor).exists())
        self.assertEqual(Visit.objects.filter(location=self.hut).count(), 2)

    def test_saving_a_location_when_a_dropped_visit_was_deleted_meanwhile(self):
        kept = self._visit([self.owner])
        dropped = self._visit([self.owner], '2026-06-02T00:00:00Z')

        def delete_the_other(sender, instance, created=False, **kwargs):
            if instance.pk == kept.pk:
                post_save.disconnect(delete_the_other, sender=Visit)
                Visit.objects.filter(pk=dropped.pk).delete()

        post_save.connect(delete_the_other, sender=Visit)
        try:
            self.as_user(self.owner)
            response = self.client.patch(
                f'/api/locations/{self.hut.id}/',
                {'visits': [{'id': str(kept.id), 'start_date': '2026-06-01T00:00:00Z'}]}, format='json',
            )
        finally:
            post_save.disconnect(delete_the_other, sender=Visit)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(list(Location.objects.get(pk=self.hut.pk).visits.values_list('pk', flat=True)), [kept.pk])
