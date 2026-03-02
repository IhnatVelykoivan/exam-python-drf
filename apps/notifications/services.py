import logging

from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def notify_seller_listing_deactivated(listing, manager):
    """Notify the seller when a manager manually deactivates their listing."""
    try:
        send_mail(
            subject=f'Ваше оголошення #{listing.id} деактивовано',
            message=(
                f'Оголошення #{listing.id} ({listing.car_brand} {listing.car_model} {listing.year}) було деактивовано менеджером платформи.\n\n'
                f'Якщо у вас є питання, зверніться до служби підтримки.\n\n'
                f'AutoRia Clone'
            ),
            from_email='noreply@autoria.ua',
            recipient_list=[listing.seller.email],
            fail_silently=True,
        )
        logger.info(
            f'Notified seller {listing.seller.email} about deactivation of listing #{listing.id}'
        )
    except Exception as e:
        logger.error(f'Failed to notify seller about listing #{listing.id} deactivation: {e}')


def notify_manager_listing_inactive(listing):
    """Send email notification to managers when a listing becomes inactive after 3 failed edit attempts."""
    from apps.roles.models import Role
    from django.contrib.auth import get_user_model

    User = get_user_model()

    try:
        manager_role = Role.objects.get(name='manager', scope='platform')
        managers = User.objects.filter(role=manager_role, is_active=True)
        emails = list(managers.values_list('email', flat=True))

        if not emails:
            logger.warning('No active managers to notify')
            return

        send_mail(
            subject=f'Listing #{listing.id} deactivated — profanity after 3 attempts',
            message=(
                f'Listing #{listing.id} by {listing.seller.email} has been deactivated '
                f'after 3 failed profanity edit attempts.\n\n'
                f'Description:\n{listing.description}\n\n'
                f'Please review at /api/listings/pending'
            ),
            from_email='noreply@autoria.ua',
            recipient_list=emails,
            fail_silently=True,
        )
        logger.info(f'Notified {len(emails)} managers about listing #{listing.id}')
    except Exception as e:
        logger.error(f'Failed to notify managers: {e}')
