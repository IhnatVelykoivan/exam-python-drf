from datetime import timedelta

from django.db.models import Avg
from django.utils import timezone

from apps.listings.models import Listing
from .models import ListingView


def get_listing_view_counts(listing):
    """Get view counts for a listing: total, today, week, month."""
    now = timezone.now()
    views = ListingView.objects.filter(listing=listing)

    return {
        'total': views.count(),
        'today': views.filter(viewed_at__gte=now.replace(hour=0, minute=0, second=0)).count(),
        'week': views.filter(viewed_at__gte=now - timedelta(days=7)).count(),
        'month': views.filter(viewed_at__gte=now - timedelta(days=30)).count(),
    }


def get_average_price_by_region(listing):
    """Get average price in UAH for same brand+model in the same region."""
    result = Listing.objects.filter(
        car_brand=listing.car_brand,
        car_model=listing.car_model,
        region=listing.region,
        status='active',
    ).aggregate(avg_price=Avg('price_uah'))
    return result['avg_price']


def get_average_price_ukraine(listing):
    """Get average price in UAH for same brand+model across all of Ukraine."""
    result = Listing.objects.filter(
        car_brand=listing.car_brand,
        car_model=listing.car_model,
        status='active',
    ).aggregate(avg_price=Avg('price_uah'))
    return result['avg_price']


def record_view(listing, request):
    """Record a view for a listing."""
    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
    if ip and ',' in ip:
        ip = ip.split(',')[0].strip()
    ListingView.objects.create(listing=listing, viewer_ip=ip)
