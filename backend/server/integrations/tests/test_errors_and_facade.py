from django.test import SimpleTestCase, TestCase

from integrations.errors import IntegrationError, MfaRequired
from integrations.facade import (
    immich_integration_for,
    immich_integrations_by_user,
    wanderer_integration_for,
)
from integrations.models import ImmichIntegration, WandererIntegration
from integrations.services import endurain, wanderer
from users.models import CustomUser


class IntegrationErrorTests(SimpleTestCase):
    def test_every_integration_raises_the_same_error_class(self):
        self.assertIs(wanderer.IntegrationError, IntegrationError)
        self.assertIs(endurain.connection.IntegrationError, IntegrationError)

    def test_optional_fields_default_to_none(self):
        error = IntegrationError('Nope')

        self.assertEqual((str(error), error.user_message, error.status_code), ('Nope', 'Nope', None))
        # Every error carries a code and the status the API answers with.
        self.assertEqual((error.code, error.status), ('integration_error', 400))

    def test_status_code_and_code_are_kept(self):
        error = IntegrationError('Gone', status_code=404, code='x.gone')

        self.assertEqual((error.status_code, error.code, error.status), (404, 'x.gone', 404))

    def test_mfa_required_is_an_integration_error_carrying_the_username(self):
        error = MfaRequired('sam')

        self.assertIsInstance(error, IntegrationError)
        self.assertEqual((error.username, error.code), ('sam', 'endurain.mfa_required'))


class FacadeLookupTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='facade-user', email='facade-user@example.com', password='testpassword123'
        )
        self.other = CustomUser.objects.create_user(
            username='facade-other', email='facade-other@example.com', password='testpassword123'
        )

    def test_lookups_return_none_when_nothing_is_configured(self):
        self.assertIsNone(immich_integration_for(self.user))
        self.assertIsNone(wanderer_integration_for(self.user))
        self.assertEqual(immich_integrations_by_user(), {})

    def test_lookups_accept_a_user_or_a_user_id_and_ignore_other_users(self):
        immich = ImmichIntegration.objects.create(user=self.user, server_url='https://i.example', api_key='k')
        wanderer_row = WandererIntegration.objects.create(user=self.user, server_url='https://w.example', api_key='k')
        ImmichIntegration.objects.create(user=self.other, server_url='https://o.example', api_key='k')

        self.assertEqual(immich_integration_for(self.user), immich)
        self.assertEqual(immich_integration_for(self.user.id), immich)
        self.assertEqual(wanderer_integration_for(self.user), wanderer_row)
        self.assertIsNone(wanderer_integration_for(self.other))
        self.assertEqual(set(immich_integrations_by_user()), {self.user.id, self.other.id})
