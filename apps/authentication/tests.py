from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.roles.models import Permission, Role

User = get_user_model()


class AuthTestMixin:
    """Mixin to set up roles and permissions for auth tests."""

    def setUp(self):
        # Create permissions
        self.perm_view = Permission.objects.create(codename='can_view_listings', name='View')
        self.perm_create = Permission.objects.create(codename='can_create_listing', name='Create')
        self.perm_request = Permission.objects.create(codename='can_request_brand', name='Request brand')
        self.perm_stats = Permission.objects.create(codename='can_view_statistics', name='Stats')
        self.perm_edit = Permission.objects.create(codename='can_edit_own_listing', name='Edit')
        self.perm_delete = Permission.objects.create(codename='can_delete_own_listing', name='Delete own')

        # Create roles
        self.buyer_role = Role.objects.create(name='buyer', scope='platform')
        self.buyer_role.permissions.set([self.perm_view])

        self.seller_role = Role.objects.create(name='seller', scope='platform')
        self.seller_role.permissions.set([
            self.perm_view, self.perm_create, self.perm_request,
            self.perm_stats, self.perm_edit, self.perm_delete,
        ])

        self.client = APIClient()


class RegisterTests(AuthTestMixin, TestCase):
    def test_register_buyer(self):
        response = self.client.post('/api/auth/register', {
            'email': 'buyer@test.com',
            'password': 'TestPass123!',
            'role_name': 'buyer',
            'first_name': 'Test',
            'last_name': 'Buyer',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertEqual(response.data['user']['email'], 'buyer@test.com')

    def test_register_seller(self):
        response = self.client.post('/api/auth/register', {
            'email': 'seller@test.com',
            'password': 'TestPass123!',
            'role_name': 'seller',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_register_invalid_role(self):
        response = self.client.post('/api/auth/register', {
            'email': 'admin@test.com',
            'password': 'TestPass123!',
            'role_name': 'admin',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self):
        self.client.post('/api/auth/register', {
            'email': 'user@test.com',
            'password': 'TestPass123!',
            'role_name': 'buyer',
        }, format='json')
        response = self.client.post('/api/auth/register', {
            'email': 'user@test.com',
            'password': 'TestPass123!',
            'role_name': 'buyer',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(AuthTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        User.objects.create_user(
            email='user@test.com',
            password='TestPass123!',
            role=self.buyer_role,
        )

    def test_login_success(self):
        response = self.client.post('/api/auth/login', {
            'email': 'user@test.com',
            'password': 'TestPass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)

    def test_login_wrong_password(self):
        response = self.client.post('/api/auth/login', {
            'email': 'user@test.com',
            'password': 'WrongPass!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_user(self):
        response = self.client.post('/api/auth/login', {
            'email': 'nobody@test.com',
            'password': 'TestPass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_banned_user(self):
        user = User.objects.get(email='user@test.com')
        user.is_active = False
        user.save()
        response = self.client.post('/api/auth/login', {
            'email': 'user@test.com',
            'password': 'TestPass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class LogoutTests(AuthTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        User.objects.create_user(
            email='user@test.com',
            password='TestPass123!',
            role=self.buyer_role,
        )
        response = self.client.post('/api/auth/login', {
            'email': 'user@test.com',
            'password': 'TestPass123!',
        }, format='json')
        self.access_token = response.data['tokens']['access']
        self.refresh_token = response.data['tokens']['refresh']

    def test_logout_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.post('/api/auth/logout', {
            'refresh': self.refresh_token,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

    def test_logout_without_token(self):
        response = self.client.post('/api/auth/logout', {
            'refresh': self.refresh_token,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
