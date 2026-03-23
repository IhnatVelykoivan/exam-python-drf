from rest_framework.permissions import BasePermission


class HasPermission:
    """Factory for DRF permission classes based on custom Role permissions."""

    def __init__(self, codename):
        self.codename = codename

    def __call__(self):
        codename = self.codename
        class PermissionClass(BasePermission):
            def has_permission(self, request, view):
                if not request.user.is_authenticated:
                    return False
                if not request.user.role:
                    return False
                return request.user.role.permissions.filter(
                    codename=codename
                ).exists()
        PermissionClass.__name__ = f'HasPerm_{codename}'
        return PermissionClass()


class IsOwnerOrReadOnly(BasePermission):
    """Object-level permission: only the owner can modify."""

    def has_object_permission(self, request, view, obj):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return obj.seller == request.user
