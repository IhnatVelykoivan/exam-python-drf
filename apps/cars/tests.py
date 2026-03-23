from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.cars.models import BrandRequest, CarBrand, CarModel
from apps.roles.models import Permission, Role

User = get_user_model()


class CarsTestMixin:
    def setUp(self):
        # Permissions
        self.perms = {}
        for codename in [
            'can_view_listings', 'can_create_listing', 'can_edit_own_listing',
            'can_delete_own_listing', 'can_delete_any_listing', 'can_deactivate_listing',
            'can_ban_user', 'can_unban_user', 'can_view_users', 'can_create_manager',
            'can_manage_roles', 'can_manage_brands', 'can_review_brand_requests',
            'can_request_brand', 'can_view_statistics', 'can_manage_dealership',
        ]:
            self.perms[codename] = Permission.objects.create(codename=codename, name=codename)

        self.seller_role = Role.objects.create(name='seller', scope='platform')
        self.seller_role.permissions.set([
            self.perms['can_view_listings'], self.perms['can_create_listing'],
            self.perms['can_request_brand'],
        ])

        self.manager_role = Role.objects.create(name='manager', scope='platform')
        self.manager_role.permissions.set([
            self.perms['can_view_listings'], self.perms['can_review_brand_requests'],
        ])

        self.admin_role = Role.objects.create(name='admin', scope='platform')
        self.admin_role.permissions.set(self.perms.values())

        self.buyer_role = Role.objects.create(name='buyer', scope='platform')
        self.buyer_role.permissions.set([self.perms['can_view_listings']])

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
        self.manager = User.objects.create_user(
            email='manager@test.com', password='Manager123!',
            role=self.manager_role,
        )

        # Seed data
        self.brand = CarBrand.objects.create(name='BMW')
        self.model = CarModel.objects.create(brand=self.brand, name='X5')

        self.client = APIClient()

    def login_as(self, email, password):
        response = self.client.post('/api/auth/login', {
            'email': email, 'password': password,
        }, format='json')
        token = response.data['tokens']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')


# ---------------------------------------------------------------------------
# CarBrand CRUD
# ---------------------------------------------------------------------------

class CarBrandTests(CarsTestMixin, TestCase):
    def test_anonymous_can_list_brands(self):
        response = self.client.get('/api/cars/brands')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_can_retrieve_brand(self):
        response = self.client.get(f'/api/cars/brands/{self.brand.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'BMW')

    def test_admin_can_create_brand(self):
        self.login_as('admin@test.com', 'Admin123!')
        response = self.client.post('/api/cars/brands', {'name': 'Audi'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CarBrand.objects.filter(name='Audi').exists())

    def test_seller_cannot_create_brand(self):
        self.login_as('seller@test.com', 'Seller123!')
        response = self.client.post('/api/cars/brands', {'name': 'Audi'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_brand(self):
        self.login_as('admin@test.com', 'Admin123!')
        response = self.client.delete(f'/api/cars/brands/{self.brand.id}')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# CarModel CRUD
# ---------------------------------------------------------------------------

class CarModelTests(CarsTestMixin, TestCase):
    def test_anonymous_can_list_models(self):
        response = self.client.get(f'/api/cars/brands/{self.brand.id}/models')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_create_model(self):
        self.login_as('admin@test.com', 'Admin123!')
        response = self.client.post(
            f'/api/cars/brands/{self.brand.id}/models',
            {'name': '3 Series'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CarModel.objects.filter(brand=self.brand, name='3 Series').exists())

    def test_seller_cannot_create_model(self):
        self.login_as('seller@test.com', 'Seller123!')
        response = self.client.post(
            f'/api/cars/brands/{self.brand.id}/models',
            {'name': 'Z4'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# BrandRequest flow (including P0.3 approve auto-create)
# ---------------------------------------------------------------------------

class BrandRequestTests(CarsTestMixin, TestCase):
    def test_seller_can_create_request(self):
        self.login_as('seller@test.com', 'Seller123!')
        response = self.client.post('/api/cars/brand-requests', {
            'brand_name': 'Porsche',
            'model_name': 'Cayenne',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BrandRequest.objects.count(), 1)

    def test_buyer_cannot_create_request(self):
        self.login_as('buyer@test.com', 'Buyer123!')
        response = self.client.post('/api/cars/brand-requests', {
            'brand_name': 'Porsche',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_list_requests(self):
        BrandRequest.objects.create(user=self.seller, brand_name='Porsche', model_name='Cayenne')
        self.login_as('manager@test.com', 'Manager123!')
        response = self.client.get('/api/cars/brand-requests')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_seller_cannot_list_requests(self):
        self.login_as('seller@test.com', 'Seller123!')
        response = self.client.get('/api/cars/brand-requests')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_approve_creates_brand_and_model(self):
        """P0.3 fix: approving a request must create the CarBrand and CarModel."""
        req = BrandRequest.objects.create(
            user=self.seller, brand_name='Porsche', model_name='Cayenne',
        )
        self.login_as('admin@test.com', 'Admin123!')
        response = self.client.patch(
            f'/api/cars/brand-requests/{req.id}',
            {'status': 'approved', 'admin_comment': 'Approved!'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(CarBrand.objects.filter(name='Porsche').exists())
        self.assertTrue(CarModel.objects.filter(brand__name='Porsche', name='Cayenne').exists())

    def test_approve_existing_brand_creates_only_model(self):
        """If brand already exists, only the model should be created."""
        CarBrand.objects.create(name='Porsche')
        req = BrandRequest.objects.create(
            user=self.seller, brand_name='Porsche', model_name='911',
        )
        self.login_as('admin@test.com', 'Admin123!')
        self.client.patch(
            f'/api/cars/brand-requests/{req.id}',
            {'status': 'approved'},
            format='json',
        )
        self.assertEqual(CarBrand.objects.filter(name='Porsche').count(), 1)
        self.assertTrue(CarModel.objects.filter(brand__name='Porsche', name='911').exists())

    def test_reject_does_not_create_brand(self):
        req = BrandRequest.objects.create(
            user=self.seller, brand_name='Lada', model_name='Vesta',
        )
        self.login_as('admin@test.com', 'Admin123!')
        self.client.patch(
            f'/api/cars/brand-requests/{req.id}',
            {'status': 'rejected', 'admin_comment': 'Not supported'},
            format='json',
        )
        self.assertFalse(CarBrand.objects.filter(name='Lada').exists())

    def test_seller_cannot_approve_request(self):
        req = BrandRequest.objects.create(
            user=self.seller, brand_name='Porsche', model_name='Cayenne',
        )
        self.login_as('seller@test.com', 'Seller123!')
        response = self.client.patch(
            f'/api/cars/brand-requests/{req.id}',
            {'status': 'approved'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
