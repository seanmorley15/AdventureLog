from datetime import datetime, timezone

from django.test import SimpleTestCase

from core.sync import etag_for, if_match_allows


class _Stamped:
    def __init__(self, updated_at):
        self.updated_at = updated_at


class ETagTests(SimpleTestCase):
    def test_is_a_quoted_string_of_the_update_time_in_microseconds(self):
        stamped = _Stamped(datetime(2026, 1, 2, 3, 4, 5, 678901, tzinfo=timezone.utc))

        self.assertEqual(etag_for(stamped), '"1767323045678901"')

    def test_changes_with_a_one_microsecond_difference(self):
        a = _Stamped(datetime(2026, 1, 2, 3, 4, 5, 1, tzinfo=timezone.utc))
        b = _Stamped(datetime(2026, 1, 2, 3, 4, 5, 2, tzinfo=timezone.utc))

        self.assertNotEqual(etag_for(a), etag_for(b))


class IfMatchTests(SimpleTestCase):
    def test_the_current_tag_matches(self):
        self.assertTrue(if_match_allows('"1"', '"1"'))

    def test_another_tag_does_not(self):
        self.assertFalse(if_match_allows('"2"', '"1"'))

    def test_any_tag_in_a_list_may_match(self):
        self.assertTrue(if_match_allows('"2", "1"', '"1"'))

    def test_a_star_matches_anything_that_exists(self):
        self.assertTrue(if_match_allows('*', '"1"'))

    def test_a_weak_tag_never_matches(self):
        self.assertFalse(if_match_allows('W/"1"', '"1"'))

    def test_an_empty_header_matches_nothing(self):
        self.assertFalse(if_match_allows('', '"1"'))
