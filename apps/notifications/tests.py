from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.cars.models import CarBrand, CarModel
from apps.listings.models import Listing, Region
from apps.notifications.services import notify_manager_listing_inactive
from apps.notifications.tasks import send_manager_notification
from apps.roles.models import Permission, Role

User = get_user_model()


class NotificationTestMixin:
    def setUp(self):
        perm = Permission.objects.create(codename='can_view_listings', name='View listings')

        self.seller_role = Role.objects.create(name='seller', scope='platform')
        self.seller_role.permissions.set([perm])

        self.manager_role = Role.objects.create(name='manager', scope='platform')
        self.manager_role.permissions.set([perm])

        self.seller = User.objects.create_user(
            email='seller@test.com', password='Seller123!', role=self.seller_role,
        )
        self.manager1 = User.objects.create_user(
            email='mgr1@test.com', password='Mgr123!', role=self.manager_role,
        )
        self.manager2 = User.objects.create_user(
            email='mgr2@test.com', password='Mgr123!', role=self.manager_role,
        )

        brand = CarBrand.objects.create(name='BMW')
        model = CarModel.objects.create(brand=brand, name='X5')
        region = Region.objects.create(name='Київ')
        self.listing = Listing.objects.create(
            seller=self.seller, car_brand=brand, car_model=model,
            year=2022, description='Test', original_price=Decimal('25000'),
            original_currency='USD', region=region, city='Kyiv',
            status='inactive', edit_attempts=3,
        )


class NotifyManagerTests(NotificationTestMixin, TestCase):
    @patch('apps.notifications.services.send_mail')
    def test_sends_email_to_all_managers(self, mock_send_mail):
        notify_manager_listing_inactive(self.listing)
        mock_send_mail.assert_called_once()
        call_kwargs = mock_send_mail.call_args
        recipients = call_kwargs[1]['recipient_list'] if 'recipient_list' in call_kwargs[1] else call_kwargs[0][3]
        self.assertIn('mgr1@test.com', recipients)
        self.assertIn('mgr2@test.com', recipients)
        self.assertEqual(len(recipients), 2)

    @patch('apps.notifications.services.send_mail')
    def test_no_email_if_no_active_managers(self, mock_send_mail):
        self.manager1.is_active = False
        self.manager1.save()
        self.manager2.is_active = False
        self.manager2.save()
        notify_manager_listing_inactive(self.listing)
        mock_send_mail.assert_not_called()

    @patch('apps.notifications.services.send_mail')
    def test_email_subject_contains_listing_id(self, mock_send_mail):
        notify_manager_listing_inactive(self.listing)
        subject = mock_send_mail.call_args[1].get('subject') or mock_send_mail.call_args[0][0]
        self.assertIn(str(self.listing.id), subject)


class SendManagerNotificationTaskTests(NotificationTestMixin, TestCase):
    @patch('apps.notifications.services.send_mail')
    def test_task_calls_notification_service(self, mock_send_mail):
        send_manager_notification(self.listing.id)
        mock_send_mail.assert_called_once()

    @patch('apps.notifications.services.send_mail')
    def test_task_handles_nonexistent_listing(self, mock_send_mail):
        # Should not raise
        send_manager_notification(99999)
        mock_send_mail.assert_not_called()
