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
        response = self.client.post("/auth/delete-account/", self._delete_payload(), format="json")
        self.assertEqual(response.status_code, 401)

    def test_delete_account_rejects_wrong_confirmation(self):
        response = self.client.post(
            "/auth/delete-account/",
            self._delete_payload(confirmation="wrongname"),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(User.objects.filter(username="deleteuser").exists())

    def test_delete_account_rejects_wrong_password(self):
        response = self.client.post(
            "/auth/delete-account/",
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

        response = self.client.post("/auth/delete-account/", self._delete_payload(), format="json")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(User.objects.filter(username="deleteuser").exists())
        self.assertFalse(Category.objects.filter(user_id=user_id).exists())
        self.assertFalse(Location.objects.filter(user_id=user_id).exists())
        self.assertFalse(APIKey.objects.filter(pk=api_key.pk).exists())
        self.assertFalse(Subscription.objects.filter(user_id=user_id).exists())
        self.assertFalse(EmailAddress.objects.filter(user_id=user_id).exists())

    def test_delete_account_with_allauth_email_address(self):
        self._create_email_address()

        response = self.client.post("/auth/delete-account/", self._delete_payload(), format="json")

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

        response = self.client.post("/auth/delete-account/", self._delete_payload(), format="json")
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

        response = self.client.post("/auth/delete-account/", self._delete_payload(), format="json")
        self.assertEqual(response.status_code, 502)
        self.assertTrue(User.objects.filter(username="deleteuser").exists())

    def test_staff_account_cannot_self_delete(self):
        self.user.is_staff = True
        self.user.save()

        response = self.client.post("/auth/delete-account/", self._delete_payload(), format="json")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(username="deleteuser").exists())
