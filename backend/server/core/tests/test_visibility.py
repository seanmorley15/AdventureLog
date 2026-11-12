"""Who may see published things and profiles: private, signed-in users, or anyone (#1226, #1124)."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, override_settings

from core.testing import make_user
from core.visibility import (
    ProfileVisibility,
    can_read_published,
    can_see_profile,
    is_shareable,
    shareable_profiles_q,
    visible_profiles_q,
)

PRIVATE, SIGNED_IN, PUBLIC = ProfileVisibility.PRIVATE, ProfileVisibility.SIGNED_IN, ProfileVisibility.PUBLIC
User = get_user_model()


class PublishedTests(TestCase):
    def setUp(self):
        self.member = make_user('pub-member')

    @override_settings(ALLOW_PUBLIC_ACCESS=True)
    def test_published_things_are_open_to_anyone_while_public_access_is_on(self):
        self.assertTrue(can_read_published(AnonymousUser()))
        self.assertTrue(can_read_published(None))
        self.assertTrue(can_read_published(self.member))

    @override_settings(ALLOW_PUBLIC_ACCESS=False)
    def test_only_signed_in_users_read_published_things_when_public_access_is_off(self):
        self.assertFalse(can_read_published(AnonymousUser()))
        self.assertFalse(can_read_published(None))
        self.assertTrue(can_read_published(self.member))


class ProfileVisibilityTests(TestCase):
    def setUp(self):
        self.viewer = make_user('prof-viewer')
        self.people = {
            level: make_user(f'prof-{level}', profile_visibility=level) for level in (PRIVATE, SIGNED_IN, PUBLIC)
        }

    def assertSees(self, viewer, expected):
        seen = {level for level, person in self.people.items() if can_see_profile(viewer, person)}
        self.assertEqual(seen, expected)
        listed = set(
            User.objects.filter(visible_profiles_q(viewer), id__in=[p.id for p in self.people.values()])
            .values_list('profile_visibility', flat=True)
        )
        self.assertEqual(listed, expected, 'the query and the check must agree')

    @override_settings(ALLOW_PUBLIC_ACCESS=True)
    def test_signed_out_visitors_see_public_profiles_only(self):
        self.assertSees(AnonymousUser(), {PUBLIC})

    @override_settings(ALLOW_PUBLIC_ACCESS=True)
    def test_signed_in_users_also_see_profiles_shown_to_signed_in_users(self):
        self.assertSees(self.viewer, {SIGNED_IN, PUBLIC})

    @override_settings(ALLOW_PUBLIC_ACCESS=False)
    def test_signed_out_visitors_see_no_profile_when_public_access_is_off(self):
        self.assertSees(AnonymousUser(), set())

    @override_settings(ALLOW_PUBLIC_ACCESS=False)
    def test_signed_in_users_still_see_public_profiles_when_public_access_is_off(self):
        self.assertSees(self.viewer, {SIGNED_IN, PUBLIC})

    def test_everyone_sees_their_own_profile(self):
        private = self.people[PRIVATE]
        self.assertTrue(can_see_profile(private, private))
        self.assertIn(private, User.objects.filter(visible_profiles_q(private)))

    def test_signed_in_and_public_profiles_can_be_shared_with_and_private_ones_cannot(self):
        self.assertEqual(
            {level for level, person in self.people.items() if is_shareable(person)}, {SIGNED_IN, PUBLIC}
        )
        shareable = set(
            User.objects.filter(shareable_profiles_q(), id__in=[p.id for p in self.people.values()])
            .values_list('profile_visibility', flat=True)
        )
        self.assertEqual(shareable, {SIGNED_IN, PUBLIC})


class LegacyPublicProfileTests(TestCase):
    """``public_profile`` mirrors ``profile_visibility == public`` for clients that only know the switch."""

    def test_a_new_user_made_public_the_old_way_is_public(self):
        self.assertEqual(make_user('legacy-new', public_profile=True).profile_visibility, PUBLIC)

    def test_choosing_a_visibility_updates_the_old_switch(self):
        user = make_user('legacy-choose', profile_visibility=PUBLIC)
        self.assertTrue(user.public_profile)
        user.profile_visibility = SIGNED_IN
        user.save()
        user.refresh_from_db()
        self.assertFalse(user.public_profile)

    def test_turning_the_old_switch_on_makes_the_profile_public(self):
        user = make_user('legacy-on', profile_visibility=SIGNED_IN)
        user.public_profile = True
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.profile_visibility, PUBLIC)

    def test_turning_the_old_switch_off_makes_a_public_profile_private(self):
        user = make_user('legacy-off', profile_visibility=PUBLIC)
        user.public_profile = False
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.profile_visibility, PRIVATE)

    def test_the_old_switch_off_leaves_a_signed_in_profile_alone(self):
        user = make_user('legacy-keep', profile_visibility=SIGNED_IN)
        user.public_profile = False
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.profile_visibility, SIGNED_IN)
