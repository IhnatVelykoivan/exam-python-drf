from django.utils import timezone

from apps.currency.services import convert_price, get_latest_rates
from apps.notifications.services import notify_manager_listing_inactive
from .validators import check_profanity


def process_listing_creation(listing):
    """
    Process a newly created listing:
    1. Check profanity
    2. Convert prices
    """
    # Profanity check
    if check_profanity(listing.description):
        listing.status = 'needs_edit'
        listing.edit_attempts = 0
    else:
        listing.status = 'active'

    # Currency conversion
    rates = get_latest_rates()
    if rates['USD'] and rates['EUR']:
        prices = convert_price(listing.original_price, listing.original_currency, rates)
        listing.price_usd = prices['price_usd']
        listing.price_eur = prices['price_eur']
        listing.price_uah = prices['price_uah']
        listing.rate_usd_uah = prices['rate_usd_uah']
        listing.rate_eur_uah = prices['rate_eur_uah']
        listing.rate_date = timezone.now()

    listing.save()
    return listing


def process_listing_edit(listing, new_description):
    """
    Process editing a listing that has status 'needs_edit'.
    Implements the 3-attempt profanity flow.
    """
    # Block edits on inactive listings (profanity attempts exhausted)
    if listing.status == 'inactive':
        return None

    listing.description = new_description

    if listing.status != 'needs_edit':
        # Normal edit for active listings — still check profanity
        if check_profanity(new_description):
            listing.status = 'needs_edit'
            listing.edit_attempts = 0
        listing.save()
        return listing

    # Status is needs_edit — profanity flow
    if listing.edit_attempts >= 3:
        return None  # Already exhausted

    if check_profanity(new_description):
        listing.edit_attempts += 1
        if listing.edit_attempts >= 3:
            listing.status = 'inactive'
            listing.save()
            notify_manager_listing_inactive(listing)
            return listing
        listing.save()
        return listing
    else:
        listing.status = 'active'
        listing.save()
        return listing


def can_create_listing(user):
    """Check if user can create a new listing (basic = 1 max across all statuses)."""
    if user.account_type == 'premium':
        return True
    from .models import Listing
    existing_count = Listing.objects.filter(seller=user).count()
    return existing_count == 0
