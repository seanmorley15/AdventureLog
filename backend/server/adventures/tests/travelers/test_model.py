import importlib
from datetime import datetime, timezone as dt_timezone

import django.apps

from adventures.models import Visit
from adventures.tests.base import AudienceTestBase


def _start():
    return datetime(2026, 6, 1, 10, 0, tzinfo=dt_timezone.utc)


class VisitTravelersModelTests(AudienceTestBase):
    def test_backfill_sets_location_owner(self):
        visit = Visit.objects.create(location=self.hut, start_date=_start())
        visit.travelers.clear()
        migration = importlib.import_module('adventures.migrations.0092_visit_travelers')
        migration.backfill_travelers(django.apps.apps, None)
        self.assertEqual(list(visit.travelers.all()), [self.hut.user])

    def test_visit_created_without_travelers_counts_for_owner(self):
        visit = Visit.objects.create(location=self.hut, start_date=_start())
        self.assertEqual(list(visit.travelers.all()), [self.owner])

    def test_explicit_travelers_replace_default(self):
        visit = Visit.objects.create(location=self.hut, start_date=_start())
        visit.travelers.set([self.editor])
        self.assertEqual(list(visit.travelers.all()), [self.editor])
