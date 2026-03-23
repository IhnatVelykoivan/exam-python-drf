from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.cars.models import CarBrand, CarModel
from apps.listings.models import Listing, Region
from apps.roles.models import Permission, Role
from apps.statistics.models import ListingView
from apps.statistics.services import (
    get_average_price_by_region,
    get_average_price_ukraine,
    get_listing_view_counts,
    record_view,
)

User = get_user_model()


class StatisticsTestMixin:
    def setUp(self):
        # Permissions + Roles
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
            self.perms['can_view_statistics'],
        ])

        self.buyer_role = Role.objects.create(name='buyer', scope='platform')
        self.buyer_role.permissions.set([self.perms['can_view_listings']])

        self.admin_role = Role.objects.create(name='admin', scope='platform')
        self.admin_role.permissions.set(self.perms.values())

        # Users
        self.seller = User.objects.create_user(
            email='seller@test.com', password='Seller123!',
            role=self.seller_role, account_type='premium',
        )
        self.seller_basic = User.objects.create_user(
            email='basic@test.com', password='Basic123!',
            role=self.seller_role, account_type='basic',
        )
        self.buyer = User.objects.create_user(
            email='buyer@test.com', password='Buyer123!',
            role=self.buyer_role,
        )
        self.admin = User.objects.create_user(
            email='admin@test.com', password='Admin123!',
            role=self.admin_role, is_staff=True,
        )

        # Car data
        self.brand = CarBrand.objects.create(name='BMW')
        self.model = CarModel.objects.create(brand=self.brand, name='X5')
        self.region = Region.objects.create(name='Київська область')
        self.region2 = Region.objects.create(name='Львівська область')

        # Listing
        self.listing = Listing.objects.create(
            seller=self.seller, car_brand=self.brand, car_model=self.model,
            year=2022, description='Test listing', original_price=Decimal('25000'),
            original_currency='USD', region=self.region, city='Kyiv',
            mileage=50000, engine_type='gasoline', status='active',
            price_uah=Decimal('1000000'),
        )

        self.client = APIClient()

    def login_as(self, email, password):
        response = self.client.post('/api/auth/login', {
            'email': email, 'password': password,
        }, format='json')
        token = response.data['tokens']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')


# ---------------------------------------------------------------------------
# Statistics services unit tests
# ---------------------------------------------------------------------------

class ViewCountServiceTests(StatisticsTestMixin, TestCase):
    def test_empty_counts(self):
        counts = get_listing_view_counts(self.listing)
        self.assertEqual(counts['total'], 0)
        self.assertEqual(counts['today'], 0)
        self.assertEqual(counts['week'], 0)
        self.assertEqual(counts['month'], 0)

    def test_counts_with_views(self):
        now = timezone.now()
        # 3 views today
        for _ in range(3):
            ListingView.objects.create(listing=self.listing, viewer_ip='1.2.3.4')
        # 1 old view (40 days ago)
        old_view = ListingView.objects.create(listing=self.listing, viewer_ip='5.6.7.8')
        ListingView.objects.filter(id=old_view.id).update(viewed_at=now - timedelta(days=40))

        counts = get_listing_view_counts(self.listing)
        self.assertEqual(counts['total'], 4)
        self.assertEqual(counts['today'], 3)
        self.assertEqual(counts['week'], 3)
        self.assertEqual(counts['month'], 3)


class AvgPriceServiceTests(StatisticsTestMixin, TestCase):
    def test_average_price_region(self):
        # Add a second listing in same region with different price
        Listing.objects.create(
            seller=self.seller, car_brand=self.brand, car_model=self.model,
            year=2023, description='Another', original_price=Decimal('30000'),
            original_currency='USD', region=self.region, city='Kyiv',
            mileage=30000, engine_type='gasoline', status='active',
            price_uah=Decimal('2000000'),
        )
        avg = get_average_price_by_region(self.listing)
        self.assertEqual(avg, Decimal('1500000'))  # (1000000 + 2000000) / 2

    def test_average_price_ukraine(self):
        # Add listing in different region
        Listing.objects.create(
            seller=self.seller, car_brand=self.brand, car_model=self.model,
            year=2023, description='Lviv listing', original_price=Decimal('30000'),
            original_currency='USD', region=self.region2, city='Lviv',
            mileage=30000, engine_type='gasoline', status='active',
            price_uah=Decimal('2000000'),
        )
        avg = get_average_price_ukraine(self.listing)
        self.assertEqual(avg, Decimal('1500000'))

    def test_average_price_excludes_inactive(self):
        Listing.objects.create(
            seller=self.seller, car_brand=self.brand, car_model=self.model,
            year=2023, description='Inactive', original_price=Decimal('30000'),
            original_currency='USD', region=self.region, city='Kyiv',
            mileage=30000, engine_type='gasoline', status='inactive',
            price_uah=Decimal('9999999'),
        )
        avg = get_average_price_by_region(self.listing)
        self.assertEqual(avg, Decimal('1000000'))  # Only the active one


class RecordViewServiceTests(StatisticsTestMixin, TestCase):
    def test_record_view_creates_entry(self):
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.META['REMOTE_ADDR'] = '10.0.0.1'
        record_view(self.listing, request)
        self.assertEqual(ListingView.objects.count(), 1)
        self.assertEqual(ListingView.objects.first().viewer_ip, '10.0.0.1')

    def test_record_view_x_forwarded_for(self):
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.50, 70.41.3.18'
        record_view(self.listing, request)
        self.assertEqual(ListingView.objects.first().viewer_ip, '203.0.113.50')


# ---------------------------------------------------------------------------
# Statistics API tests (premium gate, ownership)
# ---------------------------------------------------------------------------

class StatisticsAPITests(StatisticsTestMixin, TestCase):
    def test_premium_owner_can_view_stats(self):
        self.login_as('seller@test.com', 'Seller123!')
        response = self.client.get(f'/api/statistics/listings/{self.listing.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('views', response.data)
        self.assertIn('avg_price_region', response.data)

    def test_basic_seller_cannot_view_stats(self):
        # Create listing owned by basic seller
        listing = Listing.objects.create(
            seller=self.seller_basic, car_brand=self.brand, car_model=self.model,
            year=2022, description='Basic listing', original_price=Decimal('20000'),
            original_currency='USD', region=self.region, city='Kyiv',
            mileage=60000, engine_type='gasoline', status='active',
        )
        self.login_as('basic@test.com', 'Basic123!')
        response = self.client.get(f'/api/statistics/listings/{listing.id}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_owner_cannot_view_stats(self):
        # seller_basic is premium=no, so let's use another premium seller
        other = User.objects.create_user(
            email='other@test.com', password='Other123!',
            role=self.seller_role, account_type='premium',
        )
        self.login_as('other@test.com', 'Other123!')
        response = self.client.get(f'/api/statistics/listings/{self.listing.id}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_view_any_stats(self):
        self.login_as('admin@test.com', 'Admin123!')
        response = self.client.get(f'/api/statistics/listings/{self.listing.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_nonexistent_listing_returns_404(self):
        self.login_as('seller@test.com', 'Seller123!')
        response = self.client.get('/api/statistics/listings/99999')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_cannot_view_stats(self):
        response = self.client.get(f'/api/statistics/listings/{self.listing.id}')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_views_endpoint(self):
        self.login_as('seller@test.com', 'Seller123!')
        response = self.client.get(f'/api/statistics/listings/{self.listing.id}/views')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total', response.data)

    def test_avg_price_endpoint(self):
        self.login_as('seller@test.com', 'Seller123!')
        response = self.client.get(f'/api/statistics/listings/{self.listing.id}/avg-price')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('avg_price_region', response.data)
        self.assertIn('region_name', response.data)
