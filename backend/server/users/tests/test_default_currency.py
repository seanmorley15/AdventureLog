from rest_framework.test import APITestCase

from users.models import CustomUser


class DefaultCurrencyTests(APITestCase):
    """Any currency in circulation can be the default (#1014)."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='traveler', email='traveler@example.com', password='testpassword'
        )
        self.client.force_authenticate(self.user)

    def test_a_currency_in_circulation_can_be_the_default(self):
        response = self.client.patch('/api/account/', {'default_currency': 'COP'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.default_currency, 'COP')

    def test_a_withdrawn_currency_cannot_be_the_default(self):
        response = self.client.patch('/api/account/', {'default_currency': 'HRK'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.default_currency, 'USD')
