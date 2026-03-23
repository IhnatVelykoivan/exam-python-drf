from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.cars.models import CarBrand, CarModel
from apps.listings.models import Listing, Region
from apps.listings.services import can_create_listing, process_listing_creation, process_listing_edit
from apps.listings.validators import check_profanity
from apps.roles.models import Permission, Role

User = get_user_model()


class ProfanityValidatorTests(TestCase):
    def test_clean_text_passes(self):
        self.assertFalse(check_profanity('Продаю автомобіль в гарному стані'))

    def test_profanity_detected(self):
        self.assertTrue(check_profanity('Цей автомобіль хуйня повна'))

    def test_empty_text_passes(self):
        self.assertFalse(check_profanity(''))

    def test_mixed_case_detected(self):
        self.assertTrue(check_profanity('Це БЛЯТЬ крута тачка'))

    def test_multiple_profanity_words(self):
        self.assertTrue(check_profanity('сука блять'))

    def test_clean_ukrainian_text(self):
        self.assertFalse(check_profanity(
            'BMW X5 2020 року, дизель, автомат, шкіра, панорама, LED фари'
        ))


# ---------------------------------------------------------------------------
# Shared test setup mixin
# ---------------------------------------------------------------------------

class ListingTestMixin:
    """Shared setup for listing tests: creates roles, users, brands, regions."""

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

        # Roles
        self.buyer_role = Role.objects.create(name='buyer', scope='platform')
        self.buyer_role.permissions.set([self.perms['can_view_listings']])

        self.seller_role = Role.objects.create(name='seller', scope='platform')
        self.seller_role.permissions.set([
            self.perms['can_view_listings'], self.perms['can_create_listing'],
            self.perms['can_edit_own_listing'], self.perms['can_delete_own_listing'],
            self.perms['can_request_brand'], self.perms['can_view_statistics'],
        ])

        self.manager_role = Role.objects.create(name='manager', scope='platform')
        self.manager_role.permissions.set([
            self.perms['can_view_listings'], self.perms['can_delete_any_listing'],
            self.perms['can_deactivate_listing'], self.perms['can_ban_user'],
            self.perms['can_unban_user'], self.perms['can_view_users'],
            self.perms['can_review_brand_requests'],
        ])

        self.admin_role = Role.objects.create(name='admin', scope='platform')
        self.admin_role.permissions.set(self.perms.values())

        # Users
        self.admin = User.objects.create_user(
            email='admin@test.com', password='Admin123!',
            role=self.admin_role, is_staff=True,
        )
        self.seller = User.objects.create_user(
            email='seller@test.com', password='Seller123!',
            role=self.seller_role,
        )
        self.seller2 = User.objects.create_user(
            email='seller2@test.com', password='Seller123!',
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

        # Car data
        self.brand = CarBrand.objects.create(name='BMW')
        self.model = CarModel.objects.create(brand=self.brand, name='X5')
        self.brand2 = CarBrand.objects.create(name='Toyota')
        self.model2 = CarModel.objects.create(brand=self.brand2, name='Camry')
        self.region = Region.objects.create(name='Київська область')

        self.client = APIClient()

    def login_as(self, email, password):
        response = self.client.post('/api/auth/login', {
            'email': email, 'password': password,
        }, format='json')
        token = response.data['tokens']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def _listing_data(self, **overrides):
        data = {
            'car_brand': self.brand.id,
            'car_model': self.model.id,
            'year': 2022,
            'description': 'Clean car in great condition',
            'original_price': '25000.00',
            'original_currency': 'USD',
            'region': self.region.id,
            'city': 'Kyiv',
            'mileage': 50000,
            'engine_type': 'gasoline',
        }
        data.update(overrides)
        return data

    def _create_listing(self, seller=None, **overrides):
        """Create a listing directly in the DB (bypassing API)."""
        seller = seller or self.seller
        return Listing.objects.create(
            seller=seller,
            car_brand=self.brand,
            car_model=self.model,
            year=2022,
            description=overrides.get('description', 'Clean car'),
            original_price=Decimal('25000'),
            original_currency='USD',
            region=self.region,
            city='Kyiv',
            mileage=50000,
            engine_type='gasoline',
            status=overrides.get('status', 'active'),
            edit_attempts=overrides.get('edit_attempts', 0),
        )


# ---------------------------------------------------------------------------
# Listing CRUD API tests
# ---------------------------------------------------------------------------

class ListingCreateTests(ListingTestMixin, TestCase):
    @patch('apps.listings.services.get_latest_rates', return_value={'USD': None, 'EUR': None})
    def test_seller_can_create_listing(self, _mock_rates):
        self.login_as('seller@test.com', 'Seller123!')
        response = self.client.post('/api/listings/', self._listing_data(), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Listing.objects.count(), 1)
        self.assertEqual(response.data['status'], 'active')

    def test_buyer_cannot_create_listing(self):
        self.login_as('buyer@test.com', 'Buyer123!')
        response = self.client.post('/api/listings/', self._listing_data(), format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_create_listing(self):
        response = self.client.post('/api/listings/', self._listing_data(), format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('apps.listings.services.get_latest_rates', return_value={'USD': None, 'EUR': None})
    def test_basic_seller_limited_to_one_listing(self, _mock_rates):
        self.login_as('seller@test.com', 'Seller123!')
        response1 = self.client.post('/api/listings/', self._listing_data(), format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        response2 = self.client.post('/api/listings/', self._listing_data(), format='json')
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)

    @patch('apps.listings.services.get_latest_rates', return_value={'USD': None, 'EUR': None})
    def test_premium_seller_can_create_multiple(self, _mock_rates):
        self.seller.account_type = 'premium'
        self.seller.save()
        self.login_as('seller@test.com', 'Seller123!')
        r1 = self.client.post('/api/listings/', self._listing_data(), format='json')
        r2 = self.client.post('/api/listings/', self._listing_data(), format='json')
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)

    @patch('apps.listings.services.get_latest_rates', return_value={'USD': None, 'EUR': None})
    def test_profanity_in_description_sets_needs_edit(self, _mock_rates):
        self.login_as('seller@test.com', 'Seller123!')
        data = self._listing_data(description='Цей автомобіль хуйня повна')
        response = self.client.post('/api/listings/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'needs_edit')

    def test_car_model_must_belong_to_brand(self):
        """P1.1 fix: car_model.brand must match car_brand."""
        self.login_as('seller@test.com', 'Seller123!')
        data = self._listing_data(car_brand=self.brand.id, car_model=self.model2.id)
        response = self.client.post('/api/listings/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('car_model', response.data)


class ListingRetrieveListTests(ListingTestMixin, TestCase):
    def test_anonymous_can_list_active_listings(self):
        self._create_listing()
        response = self.client.get('/api/listings/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_can_retrieve_listing(self):
        listing = self._create_listing()
        response = self.client.get(f'/api/listings/{listing.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], listing.id)

    def test_anonymous_cannot_see_inactive_listings(self):
        self._create_listing(status='inactive')
        response = self.client.get('/api/listings/')
        self.assertEqual(response.data['count'], 0)

    def test_seller_sees_own_inactive_in_my(self):
        self._create_listing(status='inactive')
        self.login_as('seller@test.com', 'Seller123!')
        response = self.client.get('/api/listings/my')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_manager_sees_pending_listings(self):
        self._create_listing(status='needs_edit')
        self._create_listing(status='inactive')
        self.login_as('manager@test.com', 'Manager123!')
        response = self.client.get('/api/listings/pending')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_buyer_cannot_access_pending(self):
        self.login_as('buyer@test.com', 'Buyer123!')
        response = self.client.get('/api/listings/pending')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# Listing ownership permission tests (P0.1 fix)
# ---------------------------------------------------------------------------

class ListingOwnershipTests(ListingTestMixin, TestCase):
    def test_owner_can_edit_own_listing(self):
        listing = self._create_listing()
        self.login_as('seller@test.com', 'Seller123!')
        response = self.client.patch(
            f'/api/listings/{listing.id}',
            {'description': 'Updated description'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_owner_cannot_edit_listing(self):
        """P0.1 fix: another seller must get 403 when editing."""
        listing = self._create_listing(seller=self.seller)
        self.login_as('seller2@test.com', 'Seller123!')
        response = self.client.patch(
            f'/api/listings/{listing.id}',
            {'description': 'Hacked description'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_owner_cannot_delete_listing(self):
        """P0.1 fix: another seller must get 403 when deleting."""
        listing = self._create_listing(seller=self.seller)
        self.login_as('seller2@test.com', 'Seller123!')
        response = self.client.delete(f'/api/listings/{listing.id}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_delete_own_listing(self):
        listing = self._create_listing()
        self.login_as('seller@test.com', 'Seller123!')
        response = self.client.delete(f'/api/listings/{listing.id}')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Listing.objects.count(), 0)

    def test_buyer_cannot_edit_any_listing(self):
        listing = self._create_listing()
        self.login_as('buyer@test.com', 'Buyer123!')
        response = self.client.patch(
            f'/api/listings/{listing.id}',
            {'description': 'Hacked'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# Profanity 3-attempt flow (P0.5 fix)
# ---------------------------------------------------------------------------

class ProfanityFlowTests(ListingTestMixin, TestCase):
    def test_edit_with_profanity_increments_attempts(self):
        listing = self._create_listing(status='needs_edit', edit_attempts=0)
        self.login_as('seller@test.com', 'Seller123!')
        self.client.patch(
            f'/api/listings/{listing.id}',
            {'description': 'хуйня text'},
            format='json',
        )
        listing.refresh_from_db()
        self.assertEqual(listing.edit_attempts, 1)
        self.assertEqual(listing.status, 'needs_edit')

    def test_clean_edit_reactivates_listing(self):
        listing = self._create_listing(status='needs_edit', edit_attempts=1)
        self.login_as('seller@test.com', 'Seller123!')
        self.client.patch(
            f'/api/listings/{listing.id}',
            {'description': 'Clean description no bad words'},
            format='json',
        )
        listing.refresh_from_db()
        self.assertEqual(listing.status, 'active')

    @patch('apps.listings.services.notify_manager_listing_inactive')
    def test_third_profanity_deactivates_and_notifies(self, mock_notify):
        listing = self._create_listing(status='needs_edit', edit_attempts=2)
        self.login_as('seller@test.com', 'Seller123!')
        self.client.patch(
            f'/api/listings/{listing.id}',
            {'description': 'блять again'},
            format='json',
        )
        listing.refresh_from_db()
        self.assertEqual(listing.status, 'inactive')
        self.assertEqual(listing.edit_attempts, 3)
        mock_notify.assert_called_once()

    def test_inactive_listing_cannot_be_edited(self):
        """P0.5 fix: inactive listing edit must return 403."""
        listing = self._create_listing(status='inactive', edit_attempts=3)
        self.login_as('seller@test.com', 'Seller123!')
        response = self.client.patch(
            f'/api/listings/{listing.id}',
            {'description': 'Clean text'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_inactive_listing_bypass_prevented(self):
        """P0.5 fix: cannot reset edit_attempts by editing an inactive listing."""
        listing = self._create_listing(status='inactive', edit_attempts=3)
        self.login_as('seller@test.com', 'Seller123!')
        self.client.patch(
            f'/api/listings/{listing.id}',
            {'description': 'хуйня'},
            format='json',
        )
        listing.refresh_from_db()
        # Must remain inactive with 3 attempts — NOT reset to needs_edit/0
        self.assertEqual(listing.status, 'inactive')
        self.assertEqual(listing.edit_attempts, 3)


# ---------------------------------------------------------------------------
# Manager actions (deactivate / activate)
# ---------------------------------------------------------------------------

class ManagerListingActionTests(ListingTestMixin, TestCase):
    def test_manager_can_deactivate(self):
        listing = self._create_listing()
        self.login_as('manager@test.com', 'Manager123!')
        response = self.client.patch(f'/api/listings/{listing.id}/deactivate')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        listing.refresh_from_db()
        self.assertEqual(listing.status, 'inactive')

    def test_manager_can_activate(self):
        listing = self._create_listing(status='inactive')
        self.login_as('manager@test.com', 'Manager123!')
        response = self.client.patch(f'/api/listings/{listing.id}/activate')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        listing.refresh_from_db()
        self.assertEqual(listing.status, 'active')

    def test_seller_cannot_deactivate(self):
        listing = self._create_listing()
        self.login_as('seller@test.com', 'Seller123!')
        response = self.client.patch(f'/api/listings/{listing.id}/deactivate')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# Listing service unit tests
# ---------------------------------------------------------------------------

class ListingServiceTests(ListingTestMixin, TestCase):
    @patch('apps.listings.services.get_latest_rates', return_value={'USD': Decimal('41.50'), 'EUR': Decimal('44.00')})
    def test_process_creation_converts_prices(self, _mock_rates):
        listing = self._create_listing()
        listing = process_listing_creation(listing)
        self.assertIsNotNone(listing.price_usd)
        self.assertIsNotNone(listing.price_eur)
        self.assertIsNotNone(listing.price_uah)

    @patch('apps.listings.services.get_latest_rates', return_value={'USD': None, 'EUR': None})
    def test_process_creation_skips_conversion_without_rates(self, _mock_rates):
        listing = self._create_listing()
        listing = process_listing_creation(listing)
        self.assertIsNone(listing.price_usd)

    def test_process_edit_inactive_returns_none(self):
        listing = self._create_listing(status='inactive', edit_attempts=3)
        result = process_listing_edit(listing, 'New clean description')
        self.assertIsNone(result)

    def test_can_create_listing_basic_zero(self):
        self.assertTrue(can_create_listing(self.seller))

    def test_can_create_listing_basic_has_one(self):
        self._create_listing()
        self.assertFalse(can_create_listing(self.seller))

    def test_can_create_listing_premium_unlimited(self):
        self.seller.account_type = 'premium'
        self.seller.save()
        self._create_listing()
        self.assertTrue(can_create_listing(self.seller))
