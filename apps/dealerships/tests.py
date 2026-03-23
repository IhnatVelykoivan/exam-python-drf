from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.dealerships.models import Dealership
from apps.roles.models import Permission, Role

User = get_user_model()


class DealershipTestMixin:
    def setUp(self):
        perm = Permission.objects.create(codename='can_view_listings', name='View listings')

        self.seller_role = Role.objects.create(name='seller', scope='platform')
        self.seller_role.permissions.set([perm])

        self.buyer_role = Role.objects.create(name='buyer', scope='platform')
        self.buyer_role.permissions.set([perm])

        self.seller = User.objects.create_user(
            email='seller@test.com', password='Seller123!', role=self.seller_role,
        )
        self.buyer = User.objects.create_user(
            email='buyer@test.com', password='Buyer123!', role=self.buyer_role,
        )

        self.client = APIClient()

    def login_as(self, email, password):
        response = self.client.post('/api/auth/login', {
            'email': email, 'password': password,
        }, format='json')
        token = response.data['tokens']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')


class DealershipCRUDTests(DealershipTestMixin, TestCase):
    def test_anonymous_can_list_dealerships(self):
        Dealership.objects.create(name='AutoCenter', owner=self.seller)
        response = self.client.get('/api/dealerships/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_can_retrieve_dealership(self):
        d = Dealership.objects.create(name='AutoCenter', owner=self.seller)
        response = self.client.get(f'/api/dealerships/{d.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'AutoCenter')

    def test_authenticated_user_can_create_dealership(self):
        self.login_as('seller@test.com', 'Seller123!')
        response = self.client.post('/api/dealerships/', {
            'name': 'My Dealership',
            'address': '123 Main St',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        d = Dealership.objects.get(name='My Dealership')
        self.assertEqual(d.owner, self.seller)

    def test_anonymous_cannot_create_dealership(self):
        response = self.client.post('/api/dealerships/', {
            'name': 'My Dealership',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_anonymous_cannot_delete_dealership(self):
        d = Dealership.objects.create(name='AutoCenter', owner=self.seller)
        response = self.client.delete(f'/api/dealerships/{d.id}')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
