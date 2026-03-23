from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.roles.models import Permission, Role

User = get_user_model()


class UserTestMixin:
    def setUp(self):
        # Permissions
        perms = {}
        for codename in [
            'can_view_listings', 'can_create_listing', 'can_edit_own_listing',
            'can_delete_own_listing', 'can_delete_any_listing', 'can_deactivate_listing',
            'can_ban_user', 'can_unban_user', 'can_view_users', 'can_create_manager',
            'can_manage_roles', 'can_manage_brands', 'can_review_brand_requests',
            'can_request_brand', 'can_view_statistics', 'can_manage_dealership',
        ]:
            perms[codename] = Permission.objects.create(codename=codename, name=codename)

        # Roles
        self.buyer_role = Role.objects.create(name='buyer', scope='platform')
        self.buyer_role.permissions.set([perms['can_view_listings']])

        self.seller_role = Role.objects.create(name='seller', scope='platform')
        self.seller_role.permissions.set([
            perms['can_view_listings'], perms['can_create_listing'],
            perms['can_edit_own_listing'], perms['can_delete_own_listing'],
            perms['can_request_brand'], perms['can_view_statistics'],
        ])

        self.manager_role = Role.objects.create(name='manager', scope='platform')
        self.manager_role.permissions.set([
            perms['can_view_listings'], perms['can_delete_any_listing'],
            perms['can_deactivate_listing'], perms['can_ban_user'],
            perms['can_unban_user'], perms['can_view_users'],
            perms['can_review_brand_requests'],
        ])

        self.admin_role = Role.objects.create(name='admin', scope='platform')
        self.admin_role.permissions.set(perms.values())

        # Users
        self.admin = User.objects.create_user(
            email='admin@test.com', password='Admin123!',
            role=self.admin_role, is_staff=True,
        )
        self.seller = User.objects.create_user(
            email='seller@test.com', password='Seller123!',
            role=self.seller_role,
        )
        self.buyer = User.objects.create_user(
            email='buyer@test.com', password='Buyer123!',
            role=self.buyer_role,
        )

        self.client = APIClient()

    def login_as(self, email, password):
        response = self.client.post('/api/auth/login', {
            'email': email, 'password': password,
        }, format='json')
        token = response.data['tokens']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')


class ProfileTests(UserTestMixin, TestCase):
    def test_get_my_profile(self):
        self.login_as('seller@test.com', 'Seller123!')
        response = self.client.get('/api/users/me')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'seller@test.com')

    def test_update_my_profile(self):
        self.login_as('seller@test.com', 'Seller123!')
        response = self.client.patch('/api/users/me', {
            'first_name': 'Updated',
            'phone': '+380991234567',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Updated')

    def test_anonymous_cannot_access_profile(self):
        response = self.client.get('/api/users/me')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UpgradePremiumTests(UserTestMixin, TestCase):
    def test_seller_can_upgrade(self):
        self.login_as('seller@test.com', 'Seller123!')
        response = self.client.post('/api/users/upgrade-premium')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.seller.refresh_from_db()
        self.assertEqual(self.seller.account_type, 'premium')

    def test_buyer_cannot_upgrade(self):
        self.login_as('buyer@test.com', 'Buyer123!')
        response = self.client.post('/api/users/upgrade-premium')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class BanUnbanTests(UserTestMixin, TestCase):
    def test_admin_can_ban_user(self):
        self.login_as('admin@test.com', 'Admin123!')
        response = self.client.patch(f'/api/users/{self.seller.id}/ban')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.seller.refresh_from_db()
        self.assertFalse(self.seller.is_active)

    def test_admin_can_unban_user(self):
        self.seller.is_active = False
        self.seller.save()
        self.login_as('admin@test.com', 'Admin123!')
        response = self.client.patch(f'/api/users/{self.seller.id}/unban')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.seller.refresh_from_db()
        self.assertTrue(self.seller.is_active)

    def test_buyer_cannot_ban(self):
        self.login_as('buyer@test.com', 'Buyer123!')
        response = self.client.patch(f'/api/users/{self.seller.id}/ban')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CreateManagerTests(UserTestMixin, TestCase):
    def test_admin_can_create_manager(self):
        self.login_as('admin@test.com', 'Admin123!')
        response = self.client.post('/api/users/create-manager', {
            'email': 'manager@test.com',
            'password': 'Manager123!',
            'first_name': 'Test',
            'last_name': 'Manager',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        manager = User.objects.get(email='manager@test.com')
        self.assertEqual(manager.role.name, 'manager')

    def test_seller_cannot_create_manager(self):
        self.login_as('seller@test.com', 'Seller123!')
        response = self.client.post('/api/users/create-manager', {
            'email': 'manager@test.com',
            'password': 'Manager123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
