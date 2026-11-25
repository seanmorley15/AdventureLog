from datetime import datetime, timedelta, timezone as dt_timezone

from django.utils import timezone

from adventures.models import Location, Visit
from adventures.services import travelers
from adventures.tests.base import AudienceTestBase
from adventures.utils.get_is_visited import is_location_visited


def _past():
    return datetime(2026, 6, 1, 10, 0, tzinfo=dt_timezone.utc)


class VisitedPerPersonTests(AudienceTestBase):
    def _visit(self, who, start=None):
        visit = Visit.objects.create(location=self.hut, start_date=start or _past())
        visit.travelers.set(who)
        return visit

    def test_visited_only_for_travelers(self):
        self._visit([self.editor])
        self.assertTrue(is_location_visited(self.hut, self.editor))
        self.assertFalse(is_location_visited(self.hut, self.owner))

    def test_default_user_is_owner(self):
        self._visit([self.owner])
        self.assertTrue(is_location_visited(self.hut))
        self.assertTrue(self.hut.is_visited_status())
        self.assertFalse(self.hut.is_visited_status(self.editor))

    def test_future_visit_not_visited(self):
        self._visit([self.editor], start=timezone.now() + timedelta(days=30))
        self.assertFalse(is_location_visited(self.hut, self.editor))

    def test_perspective_member_sees_own(self):
        self._visit([self.editor])
        request = type('R', (), {'user': self.viewer})()
        self.assertEqual(travelers.perspective_user(request, self.hut), self.viewer)

    def test_empty_traveler_list_counts_for_nobody(self):
        self._visit([])
        for user in (self.owner, self.editor, self.viewer):
            self.assertFalse(is_location_visited(self.hut, user))

    def test_perspective_traveler_without_membership(self):
        self._visit([self.stranger])
        request = type('R', (), {'user': self.stranger})()
        self.assertEqual(travelers.perspective_user(request, self.hut), self.stranger)

    def test_perspective_stranger_sees_owner(self):
        request = type('R', (), {'user': self.stranger})()
        self.assertEqual(travelers.perspective_user(request, self.hut), self.owner)

    def test_perspective_anonymous_sees_owner(self):
        from django.contrib.auth.models import AnonymousUser

        request = type('R', (), {'user': AnonymousUser()})()
        self.assertEqual(travelers.perspective_user(request, self.hut), self.owner)

    def test_visited_by_annotation_matches_python(self):
        self._visit([self.editor])
        future = Location.objects.create(user=self.owner, name='Later')
        later = Visit.objects.create(location=future, start_date=timezone.now() + timedelta(days=30))
        later.travelers.set([self.editor])
        for user in (self.owner, self.editor, self.viewer):
            rows = Location.objects.annotate(v=travelers.visited_by(user)).values_list('pk', 'v')
            for pk, flag in rows:
                self.assertEqual(flag, is_location_visited(Location.objects.get(pk=pk), user), (user, pk))

    def test_where_ive_been_includes_traveled_while_member(self):
        self._visit([self.editor])
        mine = Location.objects.filter(travelers.where_ive_been_q(self.editor)).distinct()
        self.assertIn(self.hut, mine)
        self.assertNotIn(self.hut, Location.objects.filter(travelers.where_ive_been_q(self.viewer)).distinct())
        self.assertNotIn(self.hut, Location.objects.filter(travelers.where_ive_been_q(self.stranger)).distinct())
