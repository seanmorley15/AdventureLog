"""An email set on an account in the Django admin shows up in Settings -> Emails (#1179)."""

from importlib import import_module

from allauth.account.models import EmailAddress
from django.apps import apps
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from users.admin import CustomUserAdmin

User = get_user_model()
backfill = import_module('users.migrations.0018_backfill_email_addresses').backfill_email_addresses


class AdminEmailRecordTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser('root', 'root@example.com', 'root-password-1')
        self.model_admin = CustomUserAdmin(User, admin.site)

    def _save_in_admin(self, user, change=True):
        request = RequestFactory().post('/admin/users/customuser/')
        request.user = self.admin_user
        self.model_admin.save_model(request, user, form=None, change=change)

    def test_email_set_in_admin_gets_an_unverified_primary_record(self):
        user = User.objects.create_user('member', password='member-password-1')
        user.email = 'member@example.com'
        self._save_in_admin(user)

        address = EmailAddress.objects.get(user=user)
        self.assertEqual(address.email, 'member@example.com')
        self.assertTrue(address.primary)
        # An admin typing an address is not proof the member owns it.
        self.assertFalse(address.verified)

    def test_saving_again_does_not_duplicate_the_record(self):
        user = User.objects.create_user('member', 'member@example.com', 'member-password-1')
        self._save_in_admin(user)
        self._save_in_admin(user)
        self.assertEqual(EmailAddress.objects.filter(user=user).count(), 1)

    def test_existing_record_is_kept_as_is(self):
        user = User.objects.create_user('member', 'Member@Example.com', 'member-password-1')
        EmailAddress.objects.create(user=user, email='member@example.com', primary=True, verified=True)
        self._save_in_admin(user)

        address = EmailAddress.objects.get(user=user)
        self.assertTrue(address.verified)
        self.assertTrue(address.primary)

    def test_changed_email_becomes_the_primary(self):
        user = User.objects.create_user('member', 'old@example.com', 'member-password-1')
        EmailAddress.objects.create(user=user, email='old@example.com', primary=True, verified=True)
        user.email = 'new@example.com'
        self._save_in_admin(user)

        primary = EmailAddress.objects.get(user=user, primary=True)
        self.assertEqual(primary.email, 'new@example.com')
        self.assertTrue(EmailAddress.objects.filter(user=user, email='old@example.com').exists())
        user.refresh_from_db()
        self.assertEqual(user.email, 'new@example.com')

    def test_account_without_email_gets_no_record(self):
        user = User.objects.create_user('member', password='member-password-1')
        self._save_in_admin(user, change=False)
        self.assertFalse(EmailAddress.objects.filter(user=user).exists())


class BackfillEmailRecordTests(TestCase):
    def test_backfill_adds_records_only_where_none_exist(self):
        missing = User.objects.create_user('missing', 'missing@example.com', 'password-12345')
        recorded = User.objects.create_user('recorded', 'recorded@example.com', 'password-12345')
        EmailAddress.objects.create(user=recorded, email='other@example.com', primary=True, verified=True)
        no_email = User.objects.create_user('noemail', password='password-12345')

        backfill(apps, None)

        address = EmailAddress.objects.get(user=missing)
        self.assertEqual(address.email, 'missing@example.com')
        self.assertTrue(address.primary)
        self.assertFalse(address.verified)
        self.assertEqual(list(EmailAddress.objects.filter(user=recorded).values_list('email', flat=True)),
                         ['other@example.com'])
        self.assertFalse(EmailAddress.objects.filter(user=no_email).exists())
