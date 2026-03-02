from decimal import Decimal

import requests

from .models import CurrencyRate

PRIVATBANK_API_URL = 'https://api.privatbank.ua/p24api/pubinfo?json&exchange&coursid=5'


def fetch_privatbank_rates():
    """Fetch cash exchange rates from PrivatBank API (coursid=5)."""
    response = requests.get(PRIVATBANK_API_URL, timeout=10)
    response.raise_for_status()
    data = response.json()

    rates = []
    for item in data:
        if item['ccy'] in ('USD', 'EUR') and item['base_ccy'] == 'UAH':
            rate = CurrencyRate.objects.create(
                ccy=item['ccy'],
                base_ccy=item['base_ccy'],
                buy=Decimal(item['buy']),
                sale=Decimal(item['sale']),
            )
            rates.append(rate)
    return rates


def get_latest_rates():
    """Get latest USD and EUR rates (sale price for conversion)."""
    usd = CurrencyRate.objects.filter(ccy='USD').first()
    eur = CurrencyRate.objects.filter(ccy='EUR').first()
    return {
        'USD': usd.sale if usd else None,
        'EUR': eur.sale if eur else None,
    }


def convert_price(amount, from_currency, rates):
    """
    Convert price to all three currencies using sale rates.

    Returns dict with price_usd, price_eur, price_uah, rate_usd_uah, rate_eur_uah.
    """
    amount = Decimal(str(amount))
    rate_usd_uah = rates['USD']
    rate_eur_uah = rates['EUR']

    if not rate_usd_uah or not rate_eur_uah:
        raise ValueError('Currency rates not available')

    if from_currency == 'UAH':
        price_uah = amount
        price_usd = amount / rate_usd_uah
        price_eur = amount / rate_eur_uah
    elif from_currency == 'USD':
        price_usd = amount
        price_uah = amount * rate_usd_uah
        price_eur = price_uah / rate_eur_uah
    elif from_currency == 'EUR':
        price_eur = amount
        price_uah = amount * rate_eur_uah
        price_usd = price_uah / rate_usd_uah
    else:
        raise ValueError(f'Unsupported currency: {from_currency}')

    return {
        'price_usd': price_usd.quantize(Decimal('0.01')),
        'price_eur': price_eur.quantize(Decimal('0.01')),
        'price_uah': price_uah.quantize(Decimal('0.01')),
        'rate_usd_uah': rate_usd_uah,
        'rate_eur_uah': rate_eur_uah,
    }
