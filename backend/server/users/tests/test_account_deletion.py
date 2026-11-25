from unittest.mock import patch

from allauth.account.models import EmailAddress
from stripe.error import InvalidRequestError
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from adventures.models import Category, Location
from billing.models import Subscription
from users.models import APIKey

User = get_user_model()


class DeleteAccountTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="deleteuser",
            email="deleteuser@example.com",
            password="testpassword",
            first_name="Delete",
            last_name="User",
        )
        self.client.force_authenticate(user=self.user)

    def _create_email_address(self):
        return EmailAddress.objects.create(
            user=self.user,
            email=self.user.email,
            primary=True,
            verified=True,
        )

    def _delete_payload(self, **overrides):
        payload = {
            "confirmation": "deleteuser",
            "password": "testpassword",
        }
        payload.update(overrides)
        return payload

    def test_delete_account_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.delete("/api/account/", self._delete_payload(), format="json")
        self.assertEqual(response.status_code, 401)

    def test_delete_account_rejects_wrong_confirmation(self):
        response = self.client.delete("/api/account/",
            self._delete_payload(confirmation="wrongname"),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(User.objects.filter(username="deleteuser").exists())

    def test_delete_account_rejects_wrong_password(self):
        response = self.client.delete("/api/account/",
            self._delete_payload(password="wrongpassword"),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(User.objects.filter(username="deleteuser").exists())

    def test_delete_account_removes_user_and_data(self):
        self._create_email_address()
        Category.objects.create(user=self.user, name="test", display_name="Test", icon="🌍")
        Location.objects.create(user=self.user, name="Test Location")
        api_key, _ = APIKey.generate(user=self.user, name="Test Key")
        user_id = self.user.id

        response = self.client.delete("/api/account/", self._delete_payload(), format="json")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(User.objects.filter(username="deleteuser").exists())
        self.assertFalse(Category.objects.filter(user_id=user_id).exists())
        self.assertFalse(Location.objects.filter(user_id=user_id).exists())
        self.assertFalse(APIKey.objects.filter(pk=api_key.pk).exists())
        self.assertFalse(Subscription.objects.filter(user_id=user_id).exists())
        self.assertFalse(EmailAddress.objects.filter(user_id=user_id).exists())

    def test_delete_account_with_allauth_email_address(self):
        self._create_email_address()

        response = self.client.delete("/api/account/", self._delete_payload(), format="json")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(User.objects.filter(username="deleteuser").exists())
        self.assertFalse(EmailAddress.objects.filter(email="deleteuser@example.com").exists())

    @override_settings(CLOUD_MODE=True, STRIPE_SECRET_KEY="sk_test_fake")
    @patch("users.services.account_deletion.stripe")
    def test_delete_account_cancels_stripe_billing(self, mock_stripe):
        subscription = self.user.subscription
        subscription.stripe_customer_id = "cus_test123"
        subscription.stripe_subscription_id = "sub_test123"
        subscription.status = Subscription.STATUS_ACTIVE
        subscription.save()

        response = self.client.delete("/api/account/", self._delete_payload(), format="json")
        self.assertEqual(response.status_code, 204)
        mock_stripe.Subscription.cancel.assert_called_once_with("sub_test123")
        mock_stripe.Customer.delete.assert_called_once_with("cus_test123")

    @override_settings(CLOUD_MODE=True, STRIPE_SECRET_KEY="sk_test_fake")
    @patch("users.services.account_deletion.stripe")
    def test_delete_account_aborts_when_stripe_cancel_fails(self, mock_stripe):
        subscription = self.user.subscription
        subscription.stripe_customer_id = "cus_test123"
        subscription.stripe_subscription_id = "sub_test123"
        subscription.save()

        mock_stripe.Subscription.cancel.side_effect = InvalidRequestError(
            "failed", param="id"
        )

        response = self.client.delete("/api/account/", self._delete_payload(), format="json")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.json()["detail"],
            "Unable to delete your account because billing cleanup failed. "
            "Please try again or contact support.",
        )
        self.assertTrue(User.objects.filter(username="deleteuser").exists())

    def test_staff_account_cannot_self_delete(self):
        self.user.is_staff = True
        self.user.save()

        response = self.client.delete("/api/account/", self._delete_payload(), format="json")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(username="deleteuser").exists())


class DeleteAccountReleasesTravelersTestCase(APITestCase):
    def test_co_member_keeps_a_copy_of_a_member_place(self):
        from datetime import datetime, timezone as tz

        from adventures.models import Collection, Visit
        from users.services.account_deletion import delete_user_account

        owner = User.objects.create_user(username='downer', email='do@example.com', password='x')
        member = User.objects.create_user(username='dmember', email='dm@example.com', password='x')
        third = User.objects.create_user(username='dthird', email='dt@example.com', password='x')
        trip = Collection.objects.create(user=owner, name='Trip')
        trip.shared_with.add(member, third)
        theirs = Location.objects.create(user=member, name='Hut')
        theirs.collections.add(trip)
        mine = Location.objects.create(user=owner, name='Mine')
        mine.collections.add(trip)
        visit = Visit.objects.create(location=theirs, start_date=datetime(2026, 6, 1, tzinfo=tz.utc))
        visit.travelers.set([member, owner, third])
        gone = Visit.objects.create(location=mine, start_date=datetime(2026, 6, 1, tzinfo=tz.utc))
        gone.travelers.set([owner, third])

        delete_user_account(owner)

        left = sorted(u.pk for u in visit.travelers.all())
        self.assertEqual(left, [member.pk])
        self.assertEqual(Location.objects.filter(user=third, name='Hut').count(), 1)
        copy = Location.objects.get(user=third, name='Hut')
        self.assertEqual([u.pk for u in copy.visits.get().travelers.all()], [third.pk])
        self.assertFalse(Location.objects.filter(name='Mine').exclude(user=third).exists())
        self.assertEqual(Location.objects.filter(user=member, name='Hut').count(), 1)

    def _setup_two(self):
        from datetime import datetime, timezone as tz

        from adventures.models import Collection, Visit

        owner = User.objects.create_user(username='o2', email='o2@example.com', password='x')
        member = User.objects.create_user(username='m2', email='m2@example.com', password='x')
        third = User.objects.create_user(username='t2', email='t2@example.com', password='x')
        a = Collection.objects.create(user=owner, name='A')
        b = Collection.objects.create(user=owner, name='B')
        for c in (a, b):
            c.shared_with.add(member, third)
        hut = Location.objects.create(user=member, name='Hut')
        hut.collections.add(a, b)
        visit = Visit.objects.create(location=hut, start_date=datetime(2026, 6, 1, tzinfo=tz.utc))
        visit.travelers.set([member, third])
        return owner, member, third, hut, visit

    def test_place_in_two_of_the_owners_collections_is_released_once(self):
        from users.services.account_deletion import delete_user_account

        owner, member, third, hut, visit = self._setup_two()
        delete_user_account(owner)
        self.assertEqual([u.pk for u in visit.travelers.all()], [member.pk])
        self.assertEqual(Location.objects.filter(user=third, name='Hut').count(), 1)

    def test_traveler_reaching_the_place_through_a_third_partys_collection_is_kept(self):
        from adventures.models import Collection
        from users.services.account_deletion import delete_user_account

        owner, member, third, hut, visit = self._setup_two()
        other = Collection.objects.create(user=member, name='Mine')
        other.shared_with.add(third)
        hut.collections.add(other)
        delete_user_account(owner)
        self.assertEqual(sorted(u.pk for u in visit.travelers.all()), sorted([member.pk, third.pk]))
        self.assertFalse(Location.objects.filter(user=third).exists())


class DeleteAccountProfilePicTestCase(APITestCase):
    """The profile picture file goes only once the deletion has committed."""

    def setUp(self):
        import shutil
        import tempfile

        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root)
        override.enable()
        self.addCleanup(override.disable)
        self.user = User.objects.create_user(username='picuser', email='pic@example.com', password='pw')
        from django.core.files.base import ContentFile

        from adventures.tests.factories import PNG

        self.user.profile_pic.save('me.png', ContentFile(PNG), save=True)
        self.name = self.user.profile_pic.name

    def _exists(self):
        from django.core.files.storage import default_storage

        return default_storage.exists(self.name)

    def test_a_rolled_back_deletion_keeps_the_picture(self):
        from users.services import account_deletion

        with self.captureOnCommitCallbacks(execute=True):
            # Fails after the picture was handled, so everything before it rolls back.
            with patch.object(User, 'delete', side_effect=RuntimeError('boom')):
                with self.assertRaises(RuntimeError):
                    account_deletion.delete_user_account(self.user)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.assertTrue(self._exists())

    def test_a_committed_deletion_removes_the_picture(self):
        from users.services.account_deletion import delete_user_account

        with self.captureOnCommitCallbacks(execute=True):
            delete_user_account(self.user)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertFalse(self._exists())

    def test_a_storage_error_after_the_deletion_does_not_fail_it(self):
        from django.core.files.storage import FileSystemStorage

        from users.services.account_deletion import delete_user_account

        # The error is logged (``robust``), not raised.
        with patch.object(FileSystemStorage, 'delete', side_effect=OSError('disk gone')) as delete:
            with self.captureOnCommitCallbacks(execute=True):
                delete_user_account(self.user)
        delete.assert_called_once_with(self.name)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
