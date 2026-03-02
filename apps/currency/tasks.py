import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def fetch_currency_rates():
    """Fetch currency rates from PrivatBank and update all active listings."""
    from apps.currency.services import convert_price, fetch_privatbank_rates, get_latest_rates

    logger.info('Fetching currency rates from PrivatBank...')
    try:
        fetch_privatbank_rates()
    except Exception as e:
        logger.error(f'Failed to fetch rates: {e}')
        return

    rates = get_latest_rates()
    if not rates['USD'] or not rates['EUR']:
        logger.error('No rates available after fetch')
        return

    # Update prices in all active listings
    from apps.listings.models import Listing
    from django.utils import timezone

    listings = Listing.objects.filter(status='active')
    updated = 0
    for listing in listings:
        try:
            prices = convert_price(
                listing.original_price,
                listing.original_currency,
                rates,
            )
            listing.price_usd = prices['price_usd']
            listing.price_eur = prices['price_eur']
            listing.price_uah = prices['price_uah']
            listing.rate_usd_uah = prices['rate_usd_uah']
            listing.rate_eur_uah = prices['rate_eur_uah']
            listing.rate_date = timezone.now()
            listing.save(update_fields=[
                'price_usd', 'price_eur', 'price_uah',
                'rate_usd_uah', 'rate_eur_uah', 'rate_date',
            ])
            updated += 1
        except Exception as e:
            logger.error(f'Failed to update listing {listing.id}: {e}')

    logger.info(f'Updated prices for {updated} listings')
