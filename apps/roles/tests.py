from django.test import TestCase

from apps.roles.models import Permission, Role


class RolePermissionTests(TestCase):
    def setUp(self):
        self.perm1 = Permission.objects.create(codename='can_create_listing', name='Create listing')
        self.perm2 = Permission.objects.create(codename='can_view_listings', name='View listings')
        self.role = Role.objects.create(name='seller', scope='platform')
        self.role.permissions.set([self.perm1, self.perm2])

    def test_role_has_permission(self):
        self.assertTrue(self.role.permissions.filter(codename='can_create_listing').exists())

    def test_role_does_not_have_permission(self):
        self.assertFalse(self.role.permissions.filter(codename='can_ban_user').exists())

    def test_unique_together(self):
        with self.assertRaises(Exception):
            Role.objects.create(name='seller', scope='platform')

    def test_same_name_different_scope(self):
        role2 = Role.objects.create(name='seller', scope='dealership')
        self.assertNotEqual(self.role.id, role2.id)
