from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.cars.models import CarBrand, CarModel
from apps.currency.models import CurrencyRate
from apps.currency.services import convert_price, get_latest_rates
from apps.currency.tasks import fetch_currency_rates
from apps.listings.models import Listing, Region
from apps.roles.models import Permission, Role

User = get_user_model()


class CurrencyConversionTests(TestCase):
    def setUp(self):
        self.rates = {
            'USD': Decimal('41.5000'),
            'EUR': Decimal('44.0000'),
        }

    def test_convert_from_usd(self):
        result = convert_price(10000, 'USD', self.rates)
        self.assertEqual(result['price_usd'], Decimal('10000.00'))
        self.assertEqual(result['price_uah'], Decimal('415000.00'))
        # 415000 / 44 = 9431.818... -> 9431.82
        self.assertEqual(result['price_eur'], Decimal('9431.82'))
        self.assertEqual(result['rate_usd_uah'], Decimal('41.5000'))
        self.assertEqual(result['rate_eur_uah'], Decimal('44.0000'))

    def test_convert_from_eur(self):
        result = convert_price(10000, 'EUR', self.rates)
        self.assertEqual(result['price_eur'], Decimal('10000.00'))
        self.assertEqual(result['price_uah'], Decimal('440000.00'))
        # 440000 / 41.5 = 10602.409... -> 10602.41
        self.assertEqual(result['price_usd'], Decimal('10602.41'))

    def test_convert_from_uah(self):
        result = convert_price(415000, 'UAH', self.rates)
        self.assertEqual(result['price_uah'], Decimal('415000.00'))
        self.assertEqual(result['price_usd'], Decimal('10000.00'))
        # 415000 / 44 = 9431.818... -> 9431.82
        self.assertEqual(result['price_eur'], Decimal('9431.82'))

    def test_unsupported_currency_raises(self):
        with self.assertRaises(ValueError):
            convert_price(10000, 'GBP', self.rates)

    def test_missing_rates_raises(self):
        with self.assertRaises(ValueError):
            convert_price(10000, 'USD', {'USD': None, 'EUR': None})


class GetLatestRatesTests(TestCase):
    def test_returns_none_when_no_rates(self):
        rates = get_latest_rates()
        self.assertIsNone(rates['USD'])
        self.assertIsNone(rates['EUR'])

    def test_returns_rates_when_available(self):
        CurrencyRate.objects.create(ccy='USD', base_ccy='UAH', buy=Decimal('41.00'), sale=Decimal('41.50'))
        CurrencyRate.objects.create(ccy='EUR', base_ccy='UAH', buy=Decimal('43.50'), sale=Decimal('44.00'))
        rates = get_latest_rates()
        self.assertEqual(rates['USD'], Decimal('41.50'))
        self.assertEqual(rates['EUR'], Decimal('44.00'))


class FetchCurrencyRatesTaskTests(TestCase):
    def setUp(self):
        perm = Permission.objects.create(codename='can_view_listings', name='View')
        role = Role.objects.create(name='seller', scope='platform')
        role.permissions.set([perm])
        self.seller = User.objects.create_user(
            email='seller@test.com', password='Seller123!', role=role,
        )
        brand = CarBrand.objects.create(name='BMW')
        model = CarModel.objects.create(brand=brand, name='X5')
        region = Region.objects.create(name='Київ')
        self.listing = Listing.objects.create(
            seller=self.seller, car_brand=brand, car_model=model,
            year=2022, description='Test', original_price=Decimal('25000'),
            original_currency='USD', region=region, city='Kyiv',
            status='active',
        )

    @patch('apps.currency.services.fetch_privatbank_rates')
    @patch('apps.currency.services.get_latest_rates', return_value={
        'USD': Decimal('41.50'), 'EUR': Decimal('44.00'),
    })
    def test_task_updates_listing_prices(self, _mock_rates, _mock_fetch):
        fetch_currency_rates()
        self.listing.refresh_from_db()
        self.assertIsNotNone(self.listing.price_usd)
        self.assertIsNotNone(self.listing.price_eur)
        self.assertIsNotNone(self.listing.price_uah)
        self.assertIsNotNone(self.listing.rate_date)

    @patch('apps.currency.services.fetch_privatbank_rates', side_effect=Exception('Network error'))
    def test_task_handles_fetch_failure(self, _mock_fetch):
        # Should not raise
        fetch_currency_rates()
        self.listing.refresh_from_db()
        # Prices remain NULL since fetch failed
        self.assertIsNone(self.listing.price_usd)
