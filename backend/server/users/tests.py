from rest_framework.test import APITestCase
from .models import CustomUser
from uuid import UUID

from allauth.account.models import EmailAddress

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
