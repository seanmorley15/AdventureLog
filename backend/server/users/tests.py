from rest_framework.test import APITestCase
from .models import CustomUser
from uuid import UUID

from allauth.account.models import EmailAddress
from django.test import override_settings


class SignupLegalLinksTestCase(APITestCase):
    @override_settings(
        TERMS_OF_SERVICE_URL='https://example.com/terms',
        PRIVACY_POLICY_URL='https://example.com/privacy',
    )
    def test_signup_legal_links_endpoint_returns_configured_urls(self):
        response = self.client.get('/auth/signup-legal-links/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['terms_of_service_url'], 'https://example.com/terms')
        self.assertEqual(data['privacy_policy_url'], 'https://example.com/privacy')

    @override_settings(
        TERMS_OF_SERVICE_URL='https://example.com/terms',
        PRIVACY_POLICY_URL='https://example.com/privacy',
    )
    def test_signup_rejects_missing_terms_acceptance(self):
        response = self.client.post('/auth/browser/v1/auth/signup', {
            'username': 'termsuser',
            'email': 'termsuser@example.com',
            'password': 'testpassword',
            'first_name': 'Terms',
            'last_name': 'User',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CustomUser.objects.filter(username='termsuser').exists())

    @override_settings(
        TERMS_OF_SERVICE_URL='https://example.com/terms',
        PRIVACY_POLICY_URL='https://example.com/privacy',
    )
    def test_signup_accepts_terms_acceptance(self):
        response = self.client.post('/auth/browser/v1/auth/signup', {
            'username': 'termsaccepted',
            'email': 'termsaccepted@example.com',
            'password': 'testpassword',
            'first_name': 'Terms',
            'last_name': 'Accepted',
            'accept_terms': True,
        }, format='json')
        self.assertEqual(response.status_code, 200)
        user = CustomUser.objects.get(username='termsaccepted')
        self.assertTrue(user.legal_consent)
        self.assertEqual(user.legal_consent['terms_of_service_url'], 'https://example.com/terms')
        self.assertEqual(user.legal_consent['privacy_policy_url'], 'https://example.com/privacy')
        self.assertIn('accepted_at', user.legal_consent)


class UserAPITestCase(APITestCase):
    
    def setUp(self):
        # Signup a new user
        response = self.client.post('/auth/browser/v1/auth/signup', {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password': 'testpassword',
            'first_name': 'Test',
            'last_name': 'User',
        }, format='json')
        self.assertEqual(response.status_code, 200)

    def test_001_user(self):
        # Fetch user metadata
        response = self.client.get('/auth/user-metadata/', format='json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['email'], 'testuser@example.com')
        self.assertEqual(data['first_name'], 'Test')
        self.assertEqual(data['last_name'], 'User')
        self.assertEqual(data['public_profile'], False)
        self.assertEqual(data['profile_pic'], None)
        self.assertEqual(UUID(data['uuid']), CustomUser.objects.get(username='testuser').uuid)
        self.assertEqual(data['is_staff'], False)
        self.assertEqual(data['has_password'], True)

    def test_002_user_update(self):
        try:
            userModel = CustomUser.objects.get(username='testuser2')
        except:
            userModel = None
    
        self.assertEqual(userModel, None)
        # Update user metadata
        response = self.client.patch('/auth/update-user/', {
            'username': 'testuser2',
            'first_name': 'Test2',
            'last_name': 'User2',
            'public_profile': True,
        }, format='json')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        # Note that the email field is not updated because that is a seperate endpoint
        userModel = CustomUser.objects.get(username='testuser2')
        self.assertEqual(data['username'], 'testuser2')
        self.assertEqual(data['email'], 'testuser@example.com')
        self.assertEqual(data['first_name'], 'Test2')
        self.assertEqual(data['last_name'], 'User2')
        self.assertEqual(data['public_profile'], True)
        self.assertEqual(data['profile_pic'], None)
        self.assertEqual(UUID(data['uuid']), CustomUser.objects.get(username='testuser2').uuid)
        self.assertEqual(data['is_staff'], False)
        self.assertEqual(data['has_password'], True)

    def test_003_user_add_email(self):
        # Update user email
        response = self.client.post('/auth/browser/v1/account/email', {
            'email': 'testuser2@example.com',
        }, format='json')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        email_data = data['data'][0]

        self.assertEqual(email_data['email'], 'testuser2@example.com')
        self.assertEqual(email_data['primary'], False)
        self.assertEqual(email_data['verified'], False)

        emails = EmailAddress.objects.filter(user=CustomUser.objects.get(username='testuser'))
        self.assertEqual(emails.count(), 2)
        # assert email are testuser@example and testuser2@example.com
        self.assertEqual(emails[1].email, 'testuser@example.com')
        self.assertEqual(emails[0].email, 'testuser2@example.com')


class PasswordPolicyTestCase(APITestCase):
    def test_password_policy_endpoint_returns_defaults(self):
        response = self.client.get('/auth/password-policy/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['min_length'], 6)
        self.assertFalse(data['validators_enabled'])

    def test_signup_legal_links_endpoint_returns_empty_by_default(self):
        response = self.client.get('/auth/signup-legal-links/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNone(data['terms_of_service_url'])
        self.assertIsNone(data['privacy_policy_url'])

    def test_signup_rejects_password_below_min_length(self):
        response = self.client.post('/auth/browser/v1/auth/signup', {
            'username': 'shortpwuser',
            'email': 'shortpwuser@example.com',
            'password': 'short',
            'first_name': 'Short',
            'last_name': 'Password',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CustomUser.objects.filter(username='shortpwuser').exists())

    def test_signup_accepts_password_at_min_length(self):
        response = self.client.post('/auth/browser/v1/auth/signup', {
            'username': 'validpwuser',
            'email': 'validpwuser@example.com',
            'password': 'valid1',
            'first_name': 'Valid',
            'last_name': 'Password',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CustomUser.objects.filter(username='validpwuser').exists())


class LoginByEmailTestCase(APITestCase):
    def setUp(self):
        self.client.post('/auth/browser/v1/auth/signup', {
            'username': 'loginbyemail',
            'email': 'loginbyemail@example.com',
            'password': 'testpassword',
            'first_name': 'Login',
            'last_name': 'ByEmail',
        }, format='json')

    def test_login_with_username(self):
        self.client.cookies.clear()
        response = self.client.post('/auth/browser/v1/auth/login', {
            'username': 'loginbyemail',
            'password': 'testpassword',
        }, format='json')
        self.assertEqual(response.status_code, 200)

    def test_login_with_email(self):
        self.client.cookies.clear()
        response = self.client.post('/auth/browser/v1/auth/login', {
            'username': 'loginbyemail@example.com',
            'password': 'testpassword',
        }, format='json')
        self.assertEqual(response.status_code, 200)


class ServerSignupRedirectTestCase(APITestCase):
    @override_settings(FRONTEND_URL='http://localhost:3000')
    def test_server_signup_page_redirects_to_frontend(self):
        response = self.client.get('/accounts/signup/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://localhost:3000/signup')

    @override_settings(FRONTEND_URL='http://localhost:3000')
    def test_server_signup_page_preserves_query_string(self):
        response = self.client.get('/accounts/signup/?invite_key=abc123')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://localhost:3000/signup?invite_key=abc123')

    def test_headless_signup_still_works_when_registration_enabled(self):
        response = self.client.post('/auth/browser/v1/auth/signup', {
            'username': 'frontenduser',
            'email': 'frontenduser@example.com',
            'password': 'testpassword',
            'first_name': 'Frontend',
            'last_name': 'User',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CustomUser.objects.filter(username='frontenduser').exists())

    @override_settings(FRONTEND_URL='http://localhost:3000')
    def test_server_signup_post_is_not_allowed(self):
        response = self.client.post('/accounts/signup/', {
            'username': 'serveruser',
            'email': 'serveruser@example.com',
            'password1': 'testpassword',
            'password2': 'testpassword',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://localhost:3000/signup')
        self.assertFalse(CustomUser.objects.filter(username='serveruser').exists())
