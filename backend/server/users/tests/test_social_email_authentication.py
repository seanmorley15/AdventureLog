"""
A social sign-in may only land in an existing account by email when that account owns the
address (GHSA-6jw2-gx96-fm2j: pre-registering someone else's email to hijack their first
social sign-in). Accounts that existed when the rule came in keep their email as
``legacy_email_login`` and are not locked out.
"""

import importlib

from allauth.account.models import EmailAddress
from allauth.core import context
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialLogin
from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import RequestFactory, TestCase

User = get_user_model()

VICTIM_EMAIL = 'victim@example.com'


class SocialEmailAuthenticationTests(TestCase):
    def setUp(self):
        app = SocialApp.objects.create(provider='github', name='GitHub', client_id='id', secret='secret')
        app.sites.add(Site.objects.get_current())

    def _lookup(self):
        """Run allauth's own lookup for a GitHub login that proves VICTIM_EMAIL."""
        request = RequestFactory().get('/')
        with context.request_context(request):
            account = SocialAccount(provider='github', uid='4242', extra_data={})
            login = SocialLogin(
                account=account,
                user=User(username='', email=VICTIM_EMAIL),
                email_addresses=[EmailAddress(email=VICTIM_EMAIL, verified=True, primary=True)],
            )
            login.lookup()
        return login

    def test_unverified_local_account_is_not_signed_into(self):
        attacker = User.objects.create_user('attacker', VICTIM_EMAIL, 'attacker-password-1')
        EmailAddress.objects.create(user=attacker, email=VICTIM_EMAIL, verified=False, primary=True)

        login = self._lookup()

        self.assertFalse(login.is_existing)
        self.assertNotEqual(login.user.pk, attacker.pk)

    def test_account_without_email_record_is_not_signed_into(self):
        # A user created outside allauth (createsuperuser, admin) has no EmailAddress row at all.
        User.objects.create_user('legacy', VICTIM_EMAIL, 'legacy-password-1')

        login = self._lookup()

        self.assertFalse(login.is_existing)

    def test_verified_account_is_signed_into(self):
        owner = User.objects.create_user('owner', VICTIM_EMAIL, 'owner-password-1')
        EmailAddress.objects.create(user=owner, email=VICTIM_EMAIL, verified=True, primary=True)

        login = self._lookup()

        self.assertTrue(login.is_existing)
        self.assertEqual(login.user.pk, owner.pk)

    def test_new_accounts_are_not_grandfathered(self):
        user = User.objects.create_user('fresh', VICTIM_EMAIL, 'fresh-password-1')
        self.assertIsNone(user.legacy_email_login)


class LegacyEmailLoginTests(SocialEmailAuthenticationTests):
    """Accounts from before the rule keep signing in by their email, and only by that one."""

    def test_existing_unverified_account_keeps_signing_in(self):
        existing = User.objects.create_user('existing', VICTIM_EMAIL, 'existing-password-1')
        EmailAddress.objects.create(user=existing, email=VICTIM_EMAIL, verified=False, primary=True)
        User.objects.filter(pk=existing.pk).update(legacy_email_login=VICTIM_EMAIL)

        login = self._lookup()

        self.assertTrue(login.is_existing)
        self.assertEqual(login.user.pk, existing.pk)

    def test_existing_account_without_email_record_keeps_signing_in(self):
        # createsuperuser: no EmailAddress row, only User.email.
        admin = User.objects.create_superuser('root', VICTIM_EMAIL, 'root-password-1')
        User.objects.filter(pk=admin.pk).update(legacy_email_login='victim@example.com')

        login = self._lookup()

        self.assertEqual(login.user.pk, admin.pk)

    def test_existing_account_that_takes_someone_elses_email_later_is_refused(self):
        # Grandfathered for its old address; switching to the victim's address gains nothing.
        attacker = User.objects.create_user('attacker', VICTIM_EMAIL, 'attacker-password-1')
        EmailAddress.objects.create(user=attacker, email=VICTIM_EMAIL, verified=False, primary=True)
        User.objects.filter(pk=attacker.pk).update(legacy_email_login='attacker@example.com')

        login = self._lookup()

        self.assertFalse(login.is_existing)


class GrandfatherMigrationTests(TestCase):
    def test_existing_emails_are_copied_lowercased(self):
        with_email = User.objects.create_user('a', 'Mixed@Example.COM', 'a-password-12')
        without_email = User.objects.create_user('b', None, 'b-password-12')
        migration = importlib.import_module('users.migrations.0015_customuser_legacy_email_login')

        migration.grandfather_existing_emails(apps, None)

        with_email.refresh_from_db()
        without_email.refresh_from_db()
        self.assertEqual(with_email.legacy_email_login, 'mixed@example.com')
        self.assertIsNone(without_email.legacy_email_login)
