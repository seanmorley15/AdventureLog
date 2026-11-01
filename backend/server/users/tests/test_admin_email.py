from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AdminUserEmailTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='adminuser',
            email='admin@example.com',
            password='testpassword123',
        )
        self.client.force_login(self.admin)

    def _change_email(self, user, email):
        response = self.client.post(
            reverse('admin:users_customuser_change', args=[user.pk]),
            {
                'username': user.username,
                'email': email,
                'is_active': 'on',
                'date_joined_0': '2025-01-01',
                'date_joined_1': '00:00:00',
                'measurement_system': user.measurement_system,
                'default_currency': user.default_currency,
                'date_format': user.date_format,
                'map_style': user.map_style,
            },
        )
        self.assertEqual(response.status_code, 302)

    def test_email_set_in_admin_is_listed_for_user(self):
        user = User.objects.create_user(username='newuser', password='testpassword123')
        self._change_email(user, 'newuser@example.com')

        address = EmailAddress.objects.get(user=user)
        self.assertEqual(address.email, 'newuser@example.com')
        self.assertTrue(address.primary)

    def test_changing_email_in_admin_makes_it_primary(self):
        user = User.objects.create_user(username='newuser', email='old@example.com', password='testpassword123')
        EmailAddress.objects.create(user=user, email='old@example.com', primary=True, verified=True)

        self._change_email(user, 'new@example.com')

        user.refresh_from_db()
        self.assertEqual(user.email, 'new@example.com')
        self.assertEqual(EmailAddress.objects.get(user=user, primary=True).email, 'new@example.com')
