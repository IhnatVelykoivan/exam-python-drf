from celery import shared_task


@shared_task
def send_manager_notification(listing_id):
    """Async task to send manager notification for inactive listings."""
    from apps.listings.models import Listing
    from apps.notifications.services import notify_manager_listing_inactive

    try:
        listing = Listing.objects.select_related('seller').get(id=listing_id)
        notify_manager_listing_inactive(listing)
    except Listing.DoesNotExist:
        pass
