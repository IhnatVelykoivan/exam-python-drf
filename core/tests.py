from decimal import Decimal
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.cars.models import CarBrand, CarModel
from apps.listings.models import Listing, Region
from apps.roles.models import Permission, Role
from core.permissions import HasPermission, IsOwnerOrReadOnly

User = get_user_model()


class HasPermissionTests(TestCase):
    def setUp(self):
        self.perm = Permission.objects.create(codename='can_create_listing', name='Create listing')
        self.role = Role.objects.create(name='seller', scope='platform')
        self.role.permissions.set([self.perm])
        self.user = User.objects.create_user(
            email='seller@test.com', password='Seller123!', role=self.role,
        )

    def test_user_with_permission_allowed(self):
        permission_class = HasPermission('can_create_listing')()
        request = MagicMock()
        request.user = self.user
        self.assertTrue(permission_class.has_permission(request, None))

    def test_user_without_permission_denied(self):
        permission_class = HasPermission('can_ban_user')()
        request = MagicMock()
        request.user = self.user
        self.assertFalse(permission_class.has_permission(request, None))

    def test_unauthenticated_denied(self):
        permission_class = HasPermission('can_create_listing')()
        request = MagicMock()
        request.user.is_authenticated = False
        self.assertFalse(permission_class.has_permission(request, None))

    def test_user_without_role_denied(self):
        user_no_role = User.objects.create_user(
            email='norole@test.com', password='NoRole123!', role=None,
        )
        permission_class = HasPermission('can_create_listing')()
        request = MagicMock()
        request.user = user_no_role
        self.assertFalse(permission_class.has_permission(request, None))


class IsOwnerOrReadOnlyTests(TestCase):
    def setUp(self):
        self.perm = Permission.objects.create(codename='can_view_listings', name='View')
        self.role = Role.objects.create(name='seller', scope='platform')
        self.role.permissions.set([self.perm])
        self.owner = User.objects.create_user(
            email='owner@test.com', password='Owner123!', role=self.role,
        )
        self.other = User.objects.create_user(
            email='other@test.com', password='Other123!', role=self.role,
        )
        brand = CarBrand.objects.create(name='BMW')
        model = CarModel.objects.create(brand=brand, name='X5')
        region = Region.objects.create(name='Київ')
        self.listing = Listing.objects.create(
            seller=self.owner, car_brand=brand, car_model=model,
            year=2022, description='Test', original_price=Decimal('25000'),
            original_currency='USD', region=region, city='Kyiv',
        )

    def test_owner_can_modify(self):
        perm = IsOwnerOrReadOnly()
        request = MagicMock()
        request.method = 'PATCH'
        request.user = self.owner
        self.assertTrue(perm.has_object_permission(request, None, self.listing))

    def test_non_owner_cannot_modify(self):
        perm = IsOwnerOrReadOnly()
        request = MagicMock()
        request.method = 'PATCH'
        request.user = self.other
        self.assertFalse(perm.has_object_permission(request, None, self.listing))

    def test_anyone_can_read(self):
        perm = IsOwnerOrReadOnly()
        request = MagicMock()
        request.method = 'GET'
        request.user = self.other
        self.assertTrue(perm.has_object_permission(request, None, self.listing))

    def test_non_owner_delete_denied(self):
        perm = IsOwnerOrReadOnly()
        request = MagicMock()
        request.method = 'DELETE'
        request.user = self.other
        self.assertFalse(perm.has_object_permission(request, None, self.listing))
